#!/bin/bash
# Reset bitunix per-day state files at CR 00:00.
# Triggered by launchd com.wally.bitunix-daily-reset.

set -euo pipefail
ROOT="${HOME}/Documents/wally-trader"
MEM="${ROOT}/.claude/profiles/bitunix/memory"

# Truncate streaks file (keep schema)
cat > "${MEM}/asset_sl_streaks.json" <<EOF
{"version": 1, "as_of_cr_date": "$(date -u +%Y-%m-%d)", "assets": {}}
EOF

# Truncate window file
cat > "${MEM}/sl_window.json" <<EOF
{"events": [], "kill_switch_active_until": null}
EOF

echo "[$(date)] bitunix daily-reset done" >> "${ROOT}/.claude/logs/bitunix_reset.log"
