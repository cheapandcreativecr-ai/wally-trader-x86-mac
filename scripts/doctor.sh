#!/usr/bin/env bash
# Health check for the wally-trader system
set -e
echo "=== wally-trader doctor ==="

VENV_PY="shared/wally_core/.venv/bin/python"

echo "[1/8] Python deps..."
$VENV_PY -c "import wally_core; print('  wally_core', wally_core.__version__)" 2>&1
$VENV_PY -c "import wally_trader_mcp; print('  wally_trader_mcp ok')" 2>&1 || echo "  wally_trader_mcp NOT installed (run: make wally-mcp-install)"

echo "[2/8] Profile env..."
echo "  WALLY_PROFILE=${WALLY_PROFILE:-unset}"
echo "  WALLY_MEMORY_BACKEND=${WALLY_MEMORY_BACKEND:-hybrid (default)}"

echo "[3/8] Memory backend..."
$VENV_PY -c "
from wally_core.memory import get_backend
import json
print('  ', json.dumps(get_backend('default').health_check()))
" 2>&1 || echo "  memory backend health check failed"

echo "[4/8] Macro cache..."
if [ -f .claude/cache/macro_events.json ]; then
    AGE_S=$(($(date +%s) - $(stat -f %m .claude/cache/macro_events.json 2>/dev/null || stat -c %Y .claude/cache/macro_events.json)))
    AGE_H=$((AGE_S / 3600))
    echo "  cache age: ${AGE_H}h"
    if [ "$AGE_H" -gt 24 ]; then
        echo "  WARN: cache is stale (>24h)"
    fi
else
    echo "  cache absent (.claude/cache/macro_events.json)"
fi

echo "[5/8] TradingView MCP..."
if [ -f tradingview-mcp/src/server.js ]; then
    echo "  tradingview-mcp/src/server.js exists"
else
    echo "  tradingview-mcp NOT built"
fi

echo "[6/8] OpenClaw skills..."
if [ -d .openclaw/skills ]; then
    AGENT_COUNT=$(find .openclaw/skills/wally-agents -name SKILL.md 2>/dev/null | wc -l | tr -d ' ')
    CMD_COUNT=$(find .openclaw/skills/wally-commands -name SKILL.md 2>/dev/null | wc -l | tr -d ' ')
    echo "  agents=$AGENT_COUNT commands=$CMD_COUNT"
else
    echo "  .openclaw missing — run: bash adapters/openclaw/install.sh"
fi

echo "[7/8] Notion (if hybrid)..."
if [ -n "${NOTION_API_KEY:-}" ]; then
    echo "  NOTION_API_KEY set"
else
    echo "  NOTION_API_KEY missing (ok if backend=local)"
fi

echo "[8/8] Locks..."
STALE=$(find .claude/profiles -name "*.lock" -mmin +1 2>/dev/null | head)
if [ -z "$STALE" ]; then
    echo "  no stale locks"
else
    echo "  WARNING: stale locks found:"
    echo "$STALE"
fi

echo "=== done ==="
