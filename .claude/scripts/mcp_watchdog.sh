#!/usr/bin/env bash
# MCP watchdog — checks wally-trader-mcp pid, restarts on crash
set -euo pipefail

REPO="/Users/josecampos/Documents/wally-trader"
VENV_PY="$REPO/shared/wally_core/.venv/bin/python"
LOG="$REPO/logs/mcp-watchdog.log"

mkdir -p "$REPO/logs"

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $*" | tee -a "$LOG"; }

# Check if wally_trader_mcp process exists
if pgrep -f "wally_trader_mcp" >/dev/null 2>&1; then
    log "+ wally-trader-mcp running"
    exit 0
fi

log "! wally-trader-mcp NOT running -- attempting restart"

# Restart via venv python
cd "$REPO"
nohup "$VENV_PY" -m wally_trader_mcp >>"$LOG" 2>&1 &
PID=$!
sleep 2

if kill -0 "$PID" 2>/dev/null; then
    log "+ Restarted wally-trader-mcp (PID $PID)"
    # macOS notification
    osascript -e "display notification \"wally-trader-mcp restarted\" with title \"Wally Trader\"" 2>/dev/null || true
    exit 0
else
    log "x Restart FAILED -- process did not start"
    osascript -e "display notification \"MCP RESTART FAILED\" with title \"Wally Trader\"" 2>/dev/null || true
    exit 1
fi
