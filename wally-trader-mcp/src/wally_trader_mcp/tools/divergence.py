"""Calibration divergence MCP tool wrapper."""
import csv
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from wally_core.calibration import compare_live_vs_backtest


def divergence_check_tool(profile: str, window_days: int = 30) -> dict:
    """Compare live trades (last N days) vs backtest baseline."""
    profiles_dir = Path(os.environ.get("WALLY_PROFILES_DIR", ".claude/profiles"))
    live_path = profiles_dir / profile / "memory" / "signals_received.csv"
    backtest_path = profiles_dir / profile / "memory" / "backtest_baseline.csv"

    since = datetime.now(timezone.utc) - timedelta(days=window_days)

    def _load(path, since_ts):
        if not path.exists():
            return []
        out = []
        with open(path) as f:
            for row in csv.DictReader(f):
                ts_str = row.get("ts") or row.get("timestamp") or row.get("date") or ""
                try:
                    if "T" in ts_str:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    else:
                        ts = datetime.fromisoformat(ts_str + "T00:00:00+00:00")
                except Exception:
                    continue
                if ts < since_ts:
                    continue
                try:
                    pnl = float(row.get("pnl_usd") or 0)
                except ValueError:
                    pnl = 0
                out.append({"pnl_usd": pnl, "outcome": row.get("outcome", "")})
        return out

    live = _load(live_path, since)
    backtest = _load(backtest_path, datetime(2020, 1, 1, tzinfo=timezone.utc))

    if not backtest:
        return {"error": "no_backtest_baseline", "live_n": len(live)}

    report = compare_live_vs_backtest(live, backtest)
    return {
        "profile": profile,
        "window_days": window_days,
        "live": report.live.__dict__,
        "backtest": report.backtest.__dict__,
        "wr_drift_pct": report.wr_drift_pct,
        "pf_drift_pct": report.pf_drift_pct,
        "sharpe_drift": report.sharpe_drift,
        "severity": report.severity,
        "flags": report.flags,
    }
