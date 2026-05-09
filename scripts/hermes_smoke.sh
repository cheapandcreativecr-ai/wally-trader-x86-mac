#!/usr/bin/env bash
# scripts/hermes_smoke.sh
# Smoke test for the Hermes operational layer (6 checks).
# Usage: bash scripts/hermes_smoke.sh
# Exit code: 0 if all pass, 1 if any fail.

set -uo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"

PASS=0
FAIL=0
SKIP=0

pass()  { echo "[PASS] $1"; ((PASS++)); }
fail()  { echo "[FAIL] $1 — $2"; ((FAIL++)); }
skip()  { echo "[SKIP] $1 — $2"; ((SKIP++)); }

echo "=== Hermes Smoke Test ==="
echo "    Repo: $REPO"
echo ""

# ── Check 1: hermes CLI on PATH ───────────────────────────────────────────────
HERMES_AVAILABLE=false
if command -v hermes >/dev/null 2>&1; then
  HERMES_VER="$(hermes --version 2>/dev/null || echo 'unknown')"
  pass "hermes CLI on PATH ($HERMES_VER)"
  HERMES_AVAILABLE=true
else
  fail "hermes CLI on PATH" "command not found — install with: curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash"
fi

# ── Check 2: ~/.hermes/skills/wally-trader/ symlink ──────────────────────────
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
EXPECTED_TARGET="$REPO/.hermes/skills"
LINK="$HERMES_HOME/skills/wally-trader"

if [ "$HERMES_AVAILABLE" = false ]; then
  skip "~/.hermes/skills/wally-trader symlink" "hermes not installed"
elif [ -L "$LINK" ]; then
  ACTUAL_TARGET="$(readlink "$LINK")"
  if [ "$ACTUAL_TARGET" = "$EXPECTED_TARGET" ]; then
    pass "~/.hermes/skills/wally-trader → $EXPECTED_TARGET"
  else
    fail "~/.hermes/skills/wally-trader symlink" "points to '$ACTUAL_TARGET', expected '$EXPECTED_TARGET'"
  fi
elif [ -d "$LINK" ]; then
  fail "~/.hermes/skills/wally-trader symlink" "path exists but is a directory, not a symlink — run: bash adapters/hermes/install.sh"
else
  fail "~/.hermes/skills/wally-trader symlink" "missing — run: bash adapters/hermes/install.sh"
fi

# ── Check 3: .hermes/skills/wally-agents/ has ≥12 SKILL.md files ─────────────
AGENTS_DIR="$REPO/.hermes/skills/wally-agents"
if [ -d "$AGENTS_DIR" ]; then
  COUNT=$(find "$AGENTS_DIR" -maxdepth 1 -name "SKILL.md" -o -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
  # Also count subdirs with SKILL.md
  SUBCOUNT=$(find "$AGENTS_DIR" -name "SKILL.md" 2>/dev/null | wc -l | tr -d ' ')
  TOTAL=$((COUNT > SUBCOUNT ? COUNT : SUBCOUNT))
  if [ "$TOTAL" -ge 12 ]; then
    pass ".hermes/skills/wally-agents/ has $TOTAL SKILL.md files (≥12)"
  else
    fail ".hermes/skills/wally-agents/ SKILL.md count" "found $TOTAL, need ≥12 — run: python3 adapters/hermes/transform.py"
  fi
else
  fail ".hermes/skills/wally-agents/ exists" "directory missing — run: bash adapters/hermes/install.sh"
fi

# ── Check 4: .hermes/skills/wally-commands/ has ≥25 SKILL.md files ───────────
CMDS_DIR="$REPO/.hermes/skills/wally-commands"
if [ -d "$CMDS_DIR" ]; then
  SUBCOUNT=$(find "$CMDS_DIR" -name "SKILL.md" 2>/dev/null | wc -l | tr -d ' ')
  if [ "$SUBCOUNT" -ge 25 ]; then
    pass ".hermes/skills/wally-commands/ has $SUBCOUNT SKILL.md files (≥25)"
  else
    fail ".hermes/skills/wally-commands/ SKILL.md count" "found $SUBCOUNT, need ≥25 — run: python3 adapters/hermes/transform.py"
  fi
else
  fail ".hermes/skills/wally-commands/ exists" "directory missing — run: bash adapters/hermes/install.sh"
fi

# ── Check 5: Hermes MCP server config entries exist ───────────────────────────
if [ "$HERMES_AVAILABLE" = false ]; then
  skip "Hermes MCP config (tradingview/wally/notion)" "hermes not installed"
else
  MCP_PASS=true
  for SRV in tradingview wally notion; do
    VAL="$(hermes config get "mcp.${SRV}.command" 2>/dev/null || true)"
    if [ -n "$VAL" ]; then
      echo "       mcp.${SRV}.command = $VAL"
    else
      echo "       mcp.${SRV}.command = (not set)"
      MCP_PASS=false
    fi
  done
  if [ "$MCP_PASS" = true ]; then
    pass "Hermes MCP config entries present (tradingview, wally, notion)"
  else
    fail "Hermes MCP config entries" "one or more servers not configured — run: bash adapters/hermes/configure_mcp.sh"
  fi
fi

# ── Check 6: Python venv + wally_trader_mcp importable ───────────────────────
VENV_PY="$REPO/shared/wally_core/.venv/bin/python"
if [ ! -f "$VENV_PY" ]; then
  fail "Python venv at shared/wally_core/.venv" "not found — run: make wally-mcp-install"
else
  if "$VENV_PY" -c "import wally_trader_mcp" 2>/dev/null; then
    PYVER="$("$VENV_PY" --version 2>&1)"
    pass "Python venv ($PYVER) + wally_trader_mcp importable"
  else
    fail "wally_trader_mcp importable" "import failed with venv at $VENV_PY — run: make wally-mcp-install"
  fi
fi

# ── Check 7: hermes_daemon_wrapper.sh exists + executable ────────────────────
WRAPPER="$REPO/adapters/hermes/hermes_daemon_wrapper.sh"
if [ -x "$WRAPPER" ]; then
  pass "daemon wrapper present + executable"
elif [ -f "$WRAPPER" ]; then
  fail "daemon wrapper executable bit" "$(basename $WRAPPER) exists but not +x — run: chmod +x $WRAPPER"
else
  fail "daemon wrapper present" "missing — run: bash adapters/hermes/install.sh"
fi

# ── Check 8: WSL detection + bridge readiness (only when on WSL) ─────────────
IS_WSL=false
if grep -qiE 'microsoft|wsl' /proc/sys/kernel/osrelease 2>/dev/null; then
  IS_WSL=true
fi

if [ "$IS_WSL" = true ]; then
  BRIDGE="$REPO/adapters/hermes/wsl_tv_bridge.sh"
  if [ -x "$BRIDGE" ]; then
    pass "WSL: tv bridge script present + executable"
  else
    fail "WSL: tv bridge" "missing or not +x — run: chmod +x $BRIDGE"
  fi

  # Source .env to honor user's TV_MCP_WIN_REPO setting if present
  if [ -f "$REPO/.env" ]; then
    set -a; . "$REPO/.env"; set +a
  fi

  WIN_NODE_EXE="${WIN_NODE_EXE:-/mnt/c/Program Files/nodejs/node.exe}"
  if [ -x "$WIN_NODE_EXE" ]; then
    pass "WSL: Windows node.exe reachable at $WIN_NODE_EXE"
  else
    fail "WSL: Windows node.exe" "not at $WIN_NODE_EXE — install Node.js on Windows or set WIN_NODE_EXE in .env"
  fi

  if [ -n "${TV_MCP_WIN_REPO:-}" ]; then
    if command -v wslpath >/dev/null 2>&1; then
      WIN_REPO_WSL="$(wslpath -u "$TV_MCP_WIN_REPO" 2>/dev/null || true)"
      if [ -n "$WIN_REPO_WSL" ] && [ -d "$WIN_REPO_WSL/tradingview-mcp" ]; then
        pass "WSL: TV_MCP_WIN_REPO points to valid Windows clone ($TV_MCP_WIN_REPO)"
      else
        fail "WSL: TV_MCP_WIN_REPO valid" "$TV_MCP_WIN_REPO does not contain tradingview-mcp/ when viewed from WSL"
      fi
    else
      skip "WSL: TV_MCP_WIN_REPO validation" "wslpath not available"
    fi
  else
    fail "WSL: TV_MCP_WIN_REPO env var" "unset — add to $REPO/.env (e.g. TV_MCP_WIN_REPO=C:\\Users\\you\\wally-trader)"
  fi
else
  skip "WSL bridge checks" "not running on WSL"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
TOTAL_CHECKED=$((PASS + FAIL))
echo ""
echo "=== Summary: $PASS/$TOTAL_CHECKED checks passing (${SKIP} skipped) ==="

if [ "$FAIL" -gt 0 ]; then
  echo ""
  echo "Run 'make hermes-install' to fix most issues."
  exit 1
fi

exit 0
