.PHONY: doctor wally-mcp-install sync-oc sync-all notion-init notion-migrate notion-rollback sync-pull test-unit test-integration test-parity test help

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

notion-init:  ## Interactive setup for Notion (prompts for API key)
	@echo "1. Visit https://www.notion.so/my-integrations and create a new integration."
	@echo "2. Copy the API key (starts with 'secret_')."
	@echo "3. Add it to your shell:"
	@echo "     export NOTION_API_KEY=secret_xxx"
	@echo "4. Then run: make notion-migrate PROFILE=<your-profile> DRY_RUN=0"

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
