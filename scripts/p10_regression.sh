#!/usr/bin/env bash
# P10 regression — verify all v2 components healthy
set -euo pipefail

echo "=== P10 Regression — wally-trader v2 ==="

VENV_PY="shared/wally_core/.venv/bin/python"
VENV_PT="shared/wally_core/.venv/bin/pytest"

echo
echo "[1/8] Full pytest suite..."
$VENV_PT shared/wally_core/tests -q 2>&1 | tail -5

echo
echo "[2/8] Critical imports..."
$VENV_PY -c "from wally_core.portfolio import compute_heat, would_breach; print('  ✓ portfolio')"
$VENV_PY -c "from wally_core.discipline import tilt_score, cooldown_active; print('  ✓ discipline')"
$VENV_PY -c "from wally_core.calibration import compare_live_vs_backtest; print('  ✓ calibration')"
$VENV_PY -c "from wally_core.audit import append, verify_chain; print('  ✓ audit')"
$VENV_PY -c "from wally_core.ops import run_all_checks; print('  ✓ ops')"
$VENV_PY -c "from wally_core.atr_sl import volatility_adjusted_sl; print('  ✓ atr_sl')"

echo
echo "[3/8] CLI scripts (--help)..."
for s in tilt_check checklist habit_tracker ascii_chart auto_sl_tp tax_tracker risk_disclosure margin_call_sim divergence_check stale_guard journal_autofill funding_alerts source_grader sync_drift_check; do
    if python3 .claude/scripts/$s.py --help >/dev/null 2>&1; then
        echo "  ✓ $s.py"
    else
        echo "  ✗ $s.py FAIL"
    fi
done

echo
echo "[4/8] Audit chain integrity..."
$VENV_PY -c "
from wally_core.audit import verify_chain
r = verify_chain()
print(f'  Chain ok={r[\"ok\"]} entries={r.get(\"n_entries\", 0)}')"

echo
echo "[5/8] Health daemon (one shot)..."
$VENV_PY .claude/scripts/health_daemon.py --once 2>&1 | head -10

echo
echo "[6/8] launchd plists exist..."
for plist in macro-refresh journal-autofill dashboard funding-monitor health-daemon backup-daily mcp-watchdog; do
    p=".claude/launchd/com.wally.${plist}.plist"
    if [ -f "$p" ]; then echo "  ✓ $plist"; else echo "  ✗ $plist MISSING"; fi
done

echo
echo "[7/8] .gitignore protects sensitive..."
for pattern in tax_ audit why_log mobile_token; do
    if grep -q "$pattern" .gitignore 2>/dev/null; then
        echo "  ✓ $pattern"
    else
        echo "  ⚠ $pattern not in .gitignore"
    fi
done

echo
echo "[8/8] Git status..."
if [ -z "$(git status --porcelain | grep -v '^??\|^[ M]M tradingview-mcp')" ]; then
    echo "  ✓ tree clean (modulo tracked-but-modified externals)"
else
    echo "  ⚠ uncommitted changes:"
    git status --short | head -10
fi

echo
echo "=== P10 regression complete ==="
