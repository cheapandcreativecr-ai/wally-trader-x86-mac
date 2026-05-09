.PHONY: doctor wally-mcp-install sync-oc sync-all notion-init notion-migrate notion-rollback sync-pull test-unit test-integration test-parity test help hermes-install hermes-smoke hermes-daemon-install hermes-daemon-uninstall hermes-status hermes-restart hermes-logs hermes-telegram-setup hermes-systemd-install hermes-systemd-uninstall hermes-doctor dashboard dashboard-install dashboard-uninstall

VENV_PY := shared/wally_core/.venv/bin/python
VENV_PIP := uv pip install --python $(VENV_PY)

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-25s %s\n", $$1, $$2}'

doctor:  ## Health check for wally-trader system
	bash scripts/doctor.sh

wally-mcp-install:  ## Install wally-core + wally-trader-mcp into venv
	$(VENV_PIP) -e shared/wally_core[test,notion]
	$(VENV_PIP) -e wally-trader-mcp[test]

sync-oc:  ## Regenerate .openclaw/ from system/
	bash adapters/openclaw/install.sh

sync-all:  ## Run install.sh for all adapters
	@for a in claude-code opencode hermes openclaw codex; do \
		echo "=== $$a ==="; bash adapters/$$a/install.sh 2>&1 | tail -3; \
	done

notion-init:  ## Interactive setup wizard for Notion memory backend
	python3 .claude/scripts/notion_init.py

notion-migrate:  ## Migrate local CSV → Notion (PROFILE=name DRY_RUN=0|1)
	@if [ -z "$(PROFILE)" ]; then echo "Usage: make notion-migrate PROFILE=<name> [DRY_RUN=0]"; exit 1; fi
	@if [ "$(DRY_RUN)" = "0" ]; then \
		$(VENV_PY) -m wally_core.memory.migrate --profile $(PROFILE); \
	else \
		$(VENV_PY) -m wally_core.memory.migrate --profile $(PROFILE) --dry-run; \
	fi

notion-rollback:  ## Export Notion → local CSV (PROFILE=name)
	@if [ -z "$(PROFILE)" ]; then echo "Usage: make notion-rollback PROFILE=<name>"; exit 1; fi
	$(VENV_PY) -m wally_core.memory.migrate --profile $(PROFILE) --rollback

sync-pull:  ## Force-pull Notion → local cache (PROFILE=name)
	@if [ -z "$(PROFILE)" ]; then echo "Usage: make sync-pull PROFILE=<name>"; exit 1; fi
	$(VENV_PY) -m wally_core.memory.migrate --profile $(PROFILE) --sync-pull

test-unit:  ## Run wally_core unit tests
	$(VENV_PY) -m pytest shared/wally_core/tests -v --tb=short

test-integration:  ## Run wally-trader-mcp integration tests
	$(VENV_PY) -m pytest wally-trader-mcp/tests -v --tb=short

test-parity:  ## Run CC↔OC parity tests (requires both harnesses installed)
	@if [ ! -d tests/parity ]; then echo "tests/parity/ not yet created — Phase 8.1/8.2"; exit 0; fi
	@for t in tests/parity/parity_*.sh; do \
		echo "Running $$t"; bash $$t || exit 1; \
	done

test:  ## Run unit + integration + adapter tests
	$(MAKE) test-unit
	$(MAKE) test-integration
	$(VENV_PY) -m pytest adapters/openclaw/test_transform.py -v

# ── Hermes operational layer ──────────────────────────────────────────────────

hermes-install:  ## Install/refresh Hermes adapter (regenerate skills + register MCPs)
	bash adapters/hermes/install.sh

hermes-smoke:  ## Smoke test the Hermes setup (6 checks)
	bash scripts/hermes_smoke.sh

hermes-daemon-install:  ## Load the Hermes daemon launchd plist
	mkdir -p logs
	cp .claude/launchd/com.wally.hermes-daemon.plist ~/Library/LaunchAgents/
	launchctl load ~/Library/LaunchAgents/com.wally.hermes-daemon.plist
	@echo "✓ Hermes daemon loaded. Check status: launchctl list | grep hermes"

hermes-daemon-uninstall:  ## Unload the Hermes daemon launchd plist
	launchctl unload ~/Library/LaunchAgents/com.wally.hermes-daemon.plist 2>/dev/null || true
	rm -f ~/Library/LaunchAgents/com.wally.hermes-daemon.plist
	@echo "✓ Hermes daemon unloaded"

hermes-status:  ## Show Hermes daemon + MCP status (cross-platform)
	@echo "=== Daemon ==="
	@if command -v launchctl >/dev/null 2>&1; then \
	  launchctl list | grep hermes || echo "  launchd: daemon not loaded"; \
	fi
	@if command -v systemctl >/dev/null 2>&1; then \
	  systemctl --user status hermes --no-pager -l 2>/dev/null | head -5 || echo "  systemd: unit not installed"; \
	fi
	@echo "=== MCPs ==="
	@command -v hermes >/dev/null 2>&1 && hermes config get mcp.tradingview.command 2>/dev/null || echo "  hermes not on PATH"

hermes-restart:  ## Restart the Hermes daemon (auto-detects launchd vs systemd)
	@if command -v launchctl >/dev/null 2>&1 && launchctl list | grep -q com.wally.hermes-daemon; then \
	  echo "→ launchctl kickstart"; \
	  launchctl kickstart -k gui/$$(id -u)/com.wally.hermes-daemon; \
	elif command -v systemctl >/dev/null 2>&1; then \
	  echo "→ systemctl --user restart hermes"; \
	  systemctl --user restart hermes; \
	else \
	  echo "❌ neither launchctl nor systemctl --user available"; exit 1; \
	fi

hermes-logs:  ## Tail the Hermes daemon log
	@mkdir -p logs
	@touch logs/hermes-daemon.log
	@tail -f logs/hermes-daemon.log

hermes-telegram-setup:  ## Interactive Telegram bot bootstrap (token + chat_id)
	bash adapters/hermes/telegram_setup.sh

hermes-systemd-install:  ## Install Hermes as systemd-user service (Linux/WSL)
	@command -v systemctl >/dev/null 2>&1 || { echo "❌ systemctl not available — this target is for Linux/WSL only"; exit 1; }
	mkdir -p logs ~/.config/systemd/user
	cp .claude/systemd/hermes.service ~/.config/systemd/user/
	systemctl --user daemon-reload
	systemctl --user enable --now hermes.service
	@echo "✓ hermes.service enabled. Status: systemctl --user status hermes"
	@echo "  To survive logout: loginctl enable-linger $$USER"

hermes-systemd-uninstall:  ## Remove Hermes systemd-user service
	-systemctl --user disable --now hermes.service 2>/dev/null || true
	rm -f ~/.config/systemd/user/hermes.service
	-systemctl --user daemon-reload 2>/dev/null || true
	@echo "✓ hermes.service removed"

hermes-doctor:  ## Extended smoke test (calls hermes-smoke + WSL/Linux specific checks)
	bash scripts/hermes_smoke.sh

# ── Dashboard ─────────────────────────────────────────────────────────────────

dashboard:  ## Run the web dashboard on localhost:8080
	$(VENV_PY) -m wally_core.dashboard_server

dashboard-install:  ## Install dashboard deps + load launchd plist
	$(VENV_PIP) -e "shared/wally_core[dashboard]"
	mkdir -p logs
	cp .claude/launchd/com.wally.dashboard.plist ~/Library/LaunchAgents/
	launchctl load ~/Library/LaunchAgents/com.wally.dashboard.plist || true
	@echo "Dashboard daemon installed. Open http://localhost:8080"

dashboard-uninstall:  ## Stop + unload dashboard daemon
	launchctl unload ~/Library/LaunchAgents/com.wally.dashboard.plist || true
	rm -f ~/Library/LaunchAgents/com.wally.dashboard.plist

# ── Reliability ops daemons ───────────────────────────────────────────────────

health:  ## Run health check once
	$(VENV_PY) .claude/scripts/health_daemon.py --once

backup:  ## Run daily backup manually
	python3 .claude/scripts/backup_daily.py

ops-install:  ## Install all 3 ops daemons (health, backup, mcp-watchdog)
	mkdir -p logs
	cp .claude/launchd/com.wally.health-daemon.plist ~/Library/LaunchAgents/
	cp .claude/launchd/com.wally.backup-daily.plist ~/Library/LaunchAgents/
	cp .claude/launchd/com.wally.mcp-watchdog.plist ~/Library/LaunchAgents/
	launchctl load ~/Library/LaunchAgents/com.wally.health-daemon.plist || true
	launchctl load ~/Library/LaunchAgents/com.wally.backup-daily.plist || true
	launchctl load ~/Library/LaunchAgents/com.wally.mcp-watchdog.plist || true
	@echo "Ops daemons loaded -- verify: launchctl list | grep wally"

ops-uninstall:  ## Unload and remove all 3 ops daemons
	launchctl unload ~/Library/LaunchAgents/com.wally.health-daemon.plist || true
	launchctl unload ~/Library/LaunchAgents/com.wally.backup-daily.plist || true
	launchctl unload ~/Library/LaunchAgents/com.wally.mcp-watchdog.plist || true
	rm -f ~/Library/LaunchAgents/com.wally.health-daemon.plist
	rm -f ~/Library/LaunchAgents/com.wally.backup-daily.plist
	rm -f ~/Library/LaunchAgents/com.wally.mcp-watchdog.plist

.PHONY: health backup ops-install ops-uninstall
