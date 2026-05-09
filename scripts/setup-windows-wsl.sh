#!/usr/bin/env bash
# =============================================================================
# setup-windows-wsl.sh — Idempotent installer for wally-trader on WSL2 Ubuntu
# Run from inside WSL Ubuntu after cloning the repo (or let it clone for you).
#
# Usage:
#   bash scripts/setup-windows-wsl.sh [--skip-sync]
#
# Flags:
#   --skip-sync   Skip the initial sync-pull from Notion (useful if offline)
# =============================================================================
set -euo pipefail

# ── Colour helpers ────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

ok()   { echo -e "${GREEN}  ✓ $*${RESET}"; }
warn() { echo -e "${YELLOW}  ⚠ $*${RESET}"; }
fail() { echo -e "${RED}  ✗ $*${RESET}"; }
info() { echo -e "    $*"; }
step() { echo -e "\n${CYAN}${BOLD}=== $* ===${RESET}"; }

# ── Argument parsing ──────────────────────────────────────────────────────────
SKIP_SYNC=0
for arg in "$@"; do
  case "$arg" in
    --skip-sync) SKIP_SYNC=1 ;;
    -h|--help)
      echo "Usage: $0 [--skip-sync]"
      echo "  --skip-sync  Skip make sync-pull (offline install)"
      exit 0
      ;;
    *) warn "Unknown flag: $arg (ignored)" ;;
  esac
done

# ── Banner ────────────────────────────────────────────────────────────────────
echo -e "\n${BOLD}╔══════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║   Wally Trader — WSL2 Ubuntu Setup  (Hermes/Windows) ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════╝${RESET}"

# =============================================================================
# Step 1 — Verify OS (must be Linux)
# =============================================================================
step "Step 1: Verify OS"
OS="$(uname -s)"
if [[ "$OS" == "Linux" ]]; then
  ok "Running on Linux ($(uname -r))"
else
  fail "This script must run inside WSL2 Ubuntu, not on $OS."
  fail "Open a WSL terminal (wsl.exe or Windows Terminal → Ubuntu) and retry."
  exit 1
fi

# Warn if not WSL
if ! grep -qi 'microsoft\|wsl' /proc/version 2>/dev/null; then
  warn "Could not detect WSL signature in /proc/version."
  warn "Script is designed for WSL2 Ubuntu — continuing anyway, but YMMV."
else
  ok "WSL2 environment confirmed"
fi

# =============================================================================
# Step 2 — Verify systemd is enabled
# =============================================================================
step "Step 2: Verify systemd"
if ! systemctl is-system-running &>/dev/null; then
  warn "systemd does not appear to be running inside WSL."
  warn "Hermes daemon setup (systemd unit) will fail later."
  echo ""
  info "To enable systemd in WSL2:"
  info "  1. Open a text editor on Windows and create/edit:"
  info "       \\\\wsl\$\\Ubuntu\\etc\\wsl.conf"
  info "  2. Add the following lines:"
  info "       [boot]"
  info "       systemd=true"
  info "  3. From PowerShell/CMD run: wsl --shutdown"
  info "  4. Re-launch Ubuntu and re-run this script."
  echo ""
  warn "Continuing without systemd — Hermes daemon install step will be skipped."
  SYSTEMD_OK=0
else
  ok "systemd is active ($(systemctl is-system-running 2>/dev/null || true))"
  SYSTEMD_OK=1
fi

# =============================================================================
# Step 3 — Install OS prerequisites
# =============================================================================
step "Step 3: Install OS prerequisites (python3, nodejs, git, make, libgomp1)"

# Update package lists once (quietly)
info "Running apt-get update..."
sudo apt-get update -qq

PKGS=(python3 python3-venv python3-pip nodejs npm git make libgomp1 curl)
MISSING_PKGS=()
for pkg in "${PKGS[@]}"; do
  if dpkg -s "$pkg" &>/dev/null; then
    ok "$pkg already installed"
  else
    MISSING_PKGS+=("$pkg")
  fi
done

if [[ ${#MISSING_PKGS[@]} -gt 0 ]]; then
  info "Installing missing packages: ${MISSING_PKGS[*]}"
  sudo apt-get install -y -qq "${MISSING_PKGS[@]}" && ok "Packages installed" || {
    fail "apt-get install failed for: ${MISSING_PKGS[*]}"
    fail "Fix apt errors above and re-run this script."
    exit 1
  }
else
  ok "All OS packages already present"
fi

# =============================================================================
# Step 4 — Install uv (Python package manager)
# =============================================================================
step "Step 4: Install uv"
if command -v uv &>/dev/null; then
  ok "uv already installed ($(uv --version))"
else
  info "Installing uv via official installer..."
  curl -fsSL https://astral.sh/uv/install.sh | sh
  # Make available in this session
  export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
  if command -v uv &>/dev/null; then
    ok "uv installed ($(uv --version))"
  else
    warn "uv installer ran but binary not found on PATH."
    warn "Add ~/.local/bin or ~/.cargo/bin to your PATH in ~/.bashrc"
    warn "Then re-run this script."
    # Non-fatal: try to continue, make wally-mcp-install may fail
  fi
fi

# =============================================================================
# Step 5 — Verify Python >= 3.11 and Node >= 22
# =============================================================================
step "Step 5: Verify Python >= 3.11 and Node >= 22"

PY_OK=1
NODE_OK=1

# Python version check
if command -v python3 &>/dev/null; then
  PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
  PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
  PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
  if [[ "$PY_MAJOR" -gt 3 ]] || ([[ "$PY_MAJOR" -eq 3 ]] && [[ "$PY_MINOR" -ge 11 ]]); then
    ok "Python $PY_VER >= 3.11"
  else
    fail "Python $PY_VER found — need >= 3.11"
    info "Install a newer Python via deadsnakes PPA:"
    info "  sudo add-apt-repository ppa:deadsnakes/ppa"
    info "  sudo apt-get install python3.11 python3.11-venv"
    PY_OK=0
  fi
else
  fail "python3 not found after install — check Step 3 errors"
  PY_OK=0
fi

# Node version check
if command -v node &>/dev/null; then
  NODE_VER=$(node --version | sed 's/v//')
  NODE_MAJOR=$(echo "$NODE_VER" | cut -d. -f1)
  if [[ "$NODE_MAJOR" -ge 22 ]]; then
    ok "Node v$NODE_VER >= 22"
  else
    warn "Node v$NODE_VER found — recommend >= 22 (Hermes requires it)"
    info "Upgrade via NodeSource or nvm:"
    info "  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -"
    info "  sudo apt-get install -y nodejs"
    NODE_OK=0
  fi
else
  fail "node not found — install via NodeSource or nvm"
  NODE_OK=0
fi

if [[ "$PY_OK" -eq 0 ]] || [[ "$NODE_OK" -eq 0 ]]; then
  warn "Version requirements not met. Some steps may fail."
  warn "Fix the issues above, then re-run this script."
fi

# =============================================================================
# Step 6 — Detect or clone the repository
# =============================================================================
step "Step 6: Detect / clone wally-trader repo"

REPO_URL="https://github.com/sasasamaes/wally-trader.git"

if [[ -f "$(pwd)/Makefile" ]] && grep -q 'wally-mcp-install' "$(pwd)/Makefile" 2>/dev/null; then
  REPO_DIR="$(pwd)"
  ok "Already inside wally-trader repo: $REPO_DIR"
elif [[ -d "$HOME/wally-trader/Makefile" ]] 2>/dev/null || [[ -f "$HOME/wally-trader/Makefile" ]]; then
  REPO_DIR="$HOME/wally-trader"
  ok "Found repo at $REPO_DIR"
  cd "$REPO_DIR"
else
  echo ""
  warn "wally-trader repo not detected in current directory or ~/wally-trader"
  read -rp "    Where should I clone it? [$HOME/wally-trader]: " CLONE_DEST
  CLONE_DEST="${CLONE_DEST:-$HOME/wally-trader}"

  if [[ -d "$CLONE_DEST/.git" ]]; then
    ok "Repo already exists at $CLONE_DEST — pulling latest"
    git -C "$CLONE_DEST" pull --ff-only || warn "git pull failed — continuing with existing state"
    REPO_DIR="$CLONE_DEST"
  else
    info "Cloning $REPO_URL → $CLONE_DEST ..."
    git clone "$REPO_URL" "$CLONE_DEST"
    REPO_DIR="$CLONE_DEST"
    ok "Repo cloned to $REPO_DIR"
  fi
  cd "$REPO_DIR"
fi

REPO_DIR="$(pwd)"
info "Working directory: $REPO_DIR"

# =============================================================================
# Step 7 — Run make wally-mcp-install
# =============================================================================
step "Step 7: make wally-mcp-install"

if ! command -v make &>/dev/null; then
  fail "make not found. Install: sudo apt-get install make"
  exit 1
fi

info "Installing wally-core + wally-trader-mcp into venv..."
if make wally-mcp-install; then
  ok "make wally-mcp-install succeeded"
else
  fail "make wally-mcp-install failed — check errors above"
  info "Common fix: ensure uv is on PATH (add ~/.local/bin to PATH in ~/.bashrc)"
  exit 1
fi

# =============================================================================
# Step 8 — Prompt for NOTION_API_KEY
# =============================================================================
step "Step 8: Configure NOTION_API_KEY"

CURRENT_KEY="${NOTION_API_KEY:-}"
if [[ -n "$CURRENT_KEY" ]]; then
  info "NOTION_API_KEY already set in environment (ends in ...${CURRENT_KEY: -4})"
  read -rp "    Use current key? [Y/n]: " USE_CURRENT
  USE_CURRENT="${USE_CURRENT:-Y}"
  if [[ "$USE_CURRENT" =~ ^[Nn] ]]; then
    CURRENT_KEY=""
  fi
fi

if [[ -z "$CURRENT_KEY" ]]; then
  echo ""
  info "You need a Notion API key to enable the HybridBackend (cross-OS state sync)."
  info "  1. Go to https://www.notion.so/my-integrations"
  info "  2. Click '+ New integration' → Internal integration"
  info "  3. Copy the 'Internal Integration Token' (starts with ntn_ or secret_)"
  info "  4. Share your target Notion pages with the integration"
  echo ""
  read -rsp "    Paste your NOTION_API_KEY (input hidden): " NOTION_API_KEY_INPUT
  echo ""
  CURRENT_KEY="${NOTION_API_KEY_INPUT}"
fi

if [[ -z "$CURRENT_KEY" ]]; then
  warn "No NOTION_API_KEY provided — Notion sync will not work."
  warn "Set NOTION_API_KEY in ~/.bashrc and re-run to enable cross-OS sync."
  NOTION_CONFIGURED=0
else
  # Add to ~/.bashrc idempotently
  BASHRC="$HOME/.bashrc"
  if grep -q "NOTION_API_KEY" "$BASHRC" 2>/dev/null; then
    ok "NOTION_API_KEY already present in ~/.bashrc"
    # Update value if different
    if ! grep -q "export NOTION_API_KEY=\"${CURRENT_KEY}\"" "$BASHRC" 2>/dev/null; then
      # Remove old line, add new
      sed -i '/export NOTION_API_KEY=/d' "$BASHRC"
      echo "export NOTION_API_KEY=\"${CURRENT_KEY}\"" >> "$BASHRC"
      ok "NOTION_API_KEY updated in ~/.bashrc"
    fi
  else
    echo "" >> "$BASHRC"
    echo "# Wally Trader — Notion backend" >> "$BASHRC"
    echo "export NOTION_API_KEY=\"${CURRENT_KEY}\"" >> "$BASHRC"
    ok "NOTION_API_KEY added to ~/.bashrc"
  fi
  # Export for this session
  export NOTION_API_KEY="$CURRENT_KEY"
  NOTION_CONFIGURED=1
fi

# =============================================================================
# Step 9 — Run make sync-pull PROFILE=bitunix
# =============================================================================
step "Step 9: make sync-pull PROFILE=bitunix"

if [[ "$SKIP_SYNC" -eq 1 ]]; then
  warn "--skip-sync flag set — skipping Notion sync"
elif [[ "$NOTION_CONFIGURED" -eq 0 ]]; then
  warn "NOTION_API_KEY not configured — skipping sync-pull"
  warn "Once configured, run: make sync-pull PROFILE=bitunix"
else
  read -rp "    Run make sync-pull PROFILE=bitunix now? [Y/n]: " RUN_SYNC
  RUN_SYNC="${RUN_SYNC:-Y}"
  if [[ "$RUN_SYNC" =~ ^[Nn] ]]; then
    warn "Skipped sync-pull. Run manually: make sync-pull PROFILE=bitunix"
  else
    info "Pulling latest state from Notion..."
    if make sync-pull PROFILE=bitunix; then
      ok "Sync-pull succeeded"
    else
      warn "sync-pull failed — may be a Notion config issue"
      warn "Check NOTION_API_KEY and database IDs in .claude/scripts/notion_init.py"
      warn "Continuing — local state is still usable"
    fi
  fi
fi

# =============================================================================
# Step 10 — Verify / install Hermes
# =============================================================================
step "Step 10: Verify Hermes installation"

HERMES_INSTALLER_URL="https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh"

if command -v hermes &>/dev/null; then
  ok "hermes found: $(command -v hermes) ($(hermes --version 2>/dev/null || echo 'version unknown'))"
  HERMES_PRESENT=1
else
  warn "hermes not found on PATH"
  read -rp "    Install Hermes now via official installer? [Y/n]: " INSTALL_HERMES
  INSTALL_HERMES="${INSTALL_HERMES:-Y}"
  if [[ "$INSTALL_HERMES" =~ ^[Nn] ]]; then
    warn "Skipping Hermes install. Install manually:"
    info "  curl -fsSL $HERMES_INSTALLER_URL | bash"
    HERMES_PRESENT=0
  else
    info "Running Hermes installer..."
    if curl -fsSL "$HERMES_INSTALLER_URL" | bash; then
      # Refresh PATH
      export PATH="$HOME/.local/bin:$PATH"
      if command -v hermes &>/dev/null; then
        ok "hermes installed: $(command -v hermes)"
        HERMES_PRESENT=1
      else
        warn "Hermes installer ran but binary not on PATH"
        warn "Add ~/.local/bin to PATH in ~/.bashrc and open a new terminal"
        HERMES_PRESENT=0
      fi
    else
      fail "Hermes installer failed — check your internet connection"
      HERMES_PRESENT=0
    fi
  fi
fi

# =============================================================================
# Step 11 — make hermes-install
# =============================================================================
step "Step 11: make hermes-install"

if [[ "$HERMES_PRESENT" -eq 0 ]]; then
  warn "hermes not on PATH — skipping make hermes-install"
  warn "After installing Hermes and adding it to PATH, run: make hermes-install"
else
  info "Registering wally-trader skills + MCPs into Hermes..."
  if make hermes-install; then
    ok "make hermes-install succeeded"
  else
    fail "make hermes-install failed — check errors above"
    warn "Common fix: ensure wally-mcp-install ran successfully (Step 7)"
  fi
fi

# =============================================================================
# Step 12 — make hermes-smoke
# =============================================================================
step "Step 12: make hermes-smoke"

if [[ "$HERMES_PRESENT" -eq 0 ]]; then
  warn "hermes not on PATH — skipping smoke test"
else
  info "Running Hermes smoke test (6 checks)..."
  if make hermes-smoke; then
    ok "All smoke checks passed"
  else
    SMOKE_EXIT=$?
    warn "Smoke test reported failures (exit $SMOKE_EXIT)"
    warn "Review output above and fix before running the daemon"
  fi
fi

# =============================================================================
# Step 13 — Systemd daemon recipe (print, do not install)
# =============================================================================
step "Step 13: systemd daemon recipe (MANUAL — print only)"

HERMES_BIN="$(command -v hermes 2>/dev/null || echo '/path/to/hermes')"
SERVICE_FILE="$HOME/.config/systemd/user/wally-hermes.service"

echo ""
echo -e "${CYAN}  ┌─ Hermes systemd daemon setup ──────────────────────────────────────┐${RESET}"
if [[ "$SYSTEMD_OK" -eq 0 ]]; then
  echo -e "${YELLOW}  │ systemd not active — enable it first (see Step 2) then run:        │${RESET}"
fi
echo -e "${CYAN}  │                                                                     │${RESET}"
echo -e "${CYAN}  │  Option A: Use built-in make target (recommended):                  │${RESET}"
echo -e "${CYAN}  │    make hermes-systemd-install                                      │${RESET}"
echo -e "${CYAN}  │                                                                     │${RESET}"
echo -e "${CYAN}  │  Option B: Manual install:                                          │${RESET}"
echo -e "${CYAN}  │    mkdir -p ~/.config/systemd/user                                  │${RESET}"
echo -e "${CYAN}  │    cp .claude/systemd/hermes.service ~/.config/systemd/user/        │${RESET}"
echo -e "${CYAN}  │    systemctl --user daemon-reload                                   │${RESET}"
echo -e "${CYAN}  │    systemctl --user enable --now wally-hermes.service               │${RESET}"
echo -e "${CYAN}  │    loginctl enable-linger \$USER   # survive logout                 │${RESET}"
echo -e "${CYAN}  │                                                                     │${RESET}"
echo -e "${CYAN}  │  Verify:                                                            │${RESET}"
echo -e "${CYAN}  │    systemctl --user status wally-hermes                             │${RESET}"
echo -e "${CYAN}  │    tail -f ${REPO_DIR}/logs/hermes-daemon.log                        │${RESET}"
echo -e "${CYAN}  └─────────────────────────────────────────────────────────────────────┘${RESET}"
echo ""

# If .claude/systemd/hermes.service is missing, print a template
SYSTEMD_SVC_SRC="${REPO_DIR}/.claude/systemd/hermes.service"
if [[ ! -f "$SYSTEMD_SRC" ]] 2>/dev/null && [[ ! -f "$SYSTEMD_SVC_SRC" ]]; then
  warn ".claude/systemd/hermes.service not found in repo"
  info "Generating template at $SERVICE_FILE (NOT installed yet):"
  echo ""
  cat <<UNIT_TEMPLATE
[Unit]
Description=Wally Trader — Hermes Telegram Bot Daemon
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=${HERMES_BIN} serve --config ${REPO_DIR}/adapters/hermes/hermes.config.json
WorkingDirectory=${REPO_DIR}
Restart=on-failure
RestartSec=10
Environment="NOTION_API_KEY=${CURRENT_KEY:-YOUR_NOTION_API_KEY}"

[Install]
WantedBy=default.target
UNIT_TEMPLATE
  echo ""
  info "Copy the above into ~/.config/systemd/user/wally-hermes.service"
  info "then: systemctl --user daemon-reload && systemctl --user enable --now wally-hermes"
fi

# =============================================================================
# Step 14 — Telegram bot next steps
# =============================================================================
step "Step 14: Telegram bot configuration (manual)"

echo ""
echo -e "${CYAN}  ┌─ Telegram bot next steps ─────────────────────────────────────────┐${RESET}"
echo -e "${CYAN}  │                                                                    │${RESET}"
echo -e "${CYAN}  │  1. Get a bot token from @BotFather on Telegram:                  │${RESET}"
echo -e "${CYAN}  │       /newbot → follow prompts → copy token                       │${RESET}"
echo -e "${CYAN}  │                                                                    │${RESET}"
echo -e "${CYAN}  │  2. Get your chat ID:                                              │${RESET}"
echo -e "${CYAN}  │       Send any message to your bot, then open:                    │${RESET}"
echo -e "${CYAN}  │       https://api.telegram.org/bot<TOKEN>/getUpdates              │${RESET}"
echo -e "${CYAN}  │       Look for \"chat\":{\"id\":<YOUR_CHAT_ID>}                       │${RESET}"
echo -e "${CYAN}  │                                                                    │${RESET}"
echo -e "${CYAN}  │  3. Configure Hermes:                                              │${RESET}"
echo -e "${CYAN}  │       hermes config set telegram.bot_token \"YOUR_TOKEN\"           │${RESET}"
echo -e "${CYAN}  │       hermes config set telegram.allowed_chat_ids '[YOUR_ID]'     │${RESET}"
echo -e "${CYAN}  │                                                                    │${RESET}"
echo -e "${CYAN}  │  4. Or use interactive helper:                                     │${RESET}"
echo -e "${CYAN}  │       make hermes-telegram-setup                                  │${RESET}"
echo -e "${CYAN}  │                                                                    │${RESET}"
echo -e "${CYAN}  │  5. Smoke test from Telegram: send /regime to your bot            │${RESET}"
echo -e "${CYAN}  └────────────────────────────────────────────────────────────────────┘${RESET}"
echo ""

# =============================================================================
# Final summary
# =============================================================================
step "Setup complete — summary"

echo ""
SUMMARY_OK=1
check_item() {
  local label="$1"; local state="$2"
  if [[ "$state" -eq 1 ]]; then
    ok "$label"
  else
    fail "$label"
    SUMMARY_OK=0
  fi
}

check_item "OS: Linux (WSL2)"                 1
check_item "systemd active"                   "$SYSTEMD_OK"
check_item "Python >= 3.11"                   "$PY_OK"
check_item "Node >= 22"                       "$NODE_OK"
check_item "make wally-mcp-install"           1  # would have exited if failed
check_item "NOTION_API_KEY configured"        "$NOTION_CONFIGURED"
check_item "hermes on PATH"                   "$HERMES_PRESENT"

echo ""
if [[ "$SUMMARY_OK" -eq 1 ]]; then
  echo -e "${GREEN}${BOLD}  All checks passed! Wally Trader is ready on WSL2.${RESET}"
else
  echo -e "${YELLOW}${BOLD}  Setup complete with warnings. Review items marked ✗ above.${RESET}"
fi

echo ""
info "Reload your shell to pick up new env vars:"
info "  source ~/.bashrc"
echo ""
info "Quick reference:"
info "  Start daemon:  make hermes-systemd-install"
info "  Status:        make hermes-status"
info "  Logs:          make hermes-logs"
info "  Sync state:    make sync-pull PROFILE=bitunix"
info "  Smoke test:    make hermes-smoke"
echo ""
