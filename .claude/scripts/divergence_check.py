#!/usr/bin/env python3
"""Live vs backtest divergence checker — alerts when drift >threshold."""
import sys
import argparse
import csv
import json
import os
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

_SHARED = Path(__file__).resolve().parent.parent.parent / "shared/wally_core/src"
if _SHARED.exists() and str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from wally_core.calibration import compare_live_vs_backtest


def load_csv_trades(path: Path, since: datetime) -> list[dict]:
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
            if ts < since:
                continue
            pnl_str = row.get("pnl_usd") or "0"
            try:
                pnl = float(pnl_str) if pnl_str else 0.0
            except ValueError:
                pnl = 0.0
            out.append({"pnl_usd": pnl, "outcome": row.get("outcome", "")})
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--profile", required=True)
    p.add_argument("--window", default="30d", help="e.g., 7d, 30d, 90d")
    p.add_argument("--backtest-csv", help="Path to backtest baseline CSV", default=None)
    p.add_argument("--notify", action="store_true", help="macOS notify on ALERT")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    days = int(args.window.rstrip("d"))
    since = datetime.now(timezone.utc) - timedelta(days=days)

    profiles_dir = Path(os.environ.get("WALLY_PROFILES_DIR", ".claude/profiles"))
    live_path = profiles_dir / args.profile / "memory" / "signals_received.csv"
    backtest_path = Path(args.backtest_csv) if args.backtest_csv else (
        profiles_dir / args.profile / "memory" / "backtest_baseline.csv"
    )

    live_trades = load_csv_trades(live_path, since)
    backtest_trades = load_csv_trades(backtest_path, datetime(2020, 1, 1, tzinfo=timezone.utc))

    if not backtest_trades:
        msg = f"No backtest baseline at {backtest_path} — skipping divergence check"
        if args.json:
            print(json.dumps({"error": msg, "live_n": len(live_trades)}))
        else:
            print(f"WARNING: {msg}")
        sys.exit(0)

    if not live_trades:
        msg = f"No live trades in window {args.window}"
        if args.json:
            print(json.dumps({"info": msg}))
        else:
            print(f"INFO: {msg}")
        sys.exit(0)

    report = compare_live_vs_backtest(live_trades, backtest_trades)

    out = {
        "profile": args.profile,
        "window": args.window,
        "live": report.live.__dict__,
        "backtest": report.backtest.__dict__,
        "drifts": {
            "wr_pct": report.wr_drift_pct,
            "pf_pct": report.pf_drift_pct,
            "sharpe": report.sharpe_drift,
        },
        "severity": report.severity,
        "flags": report.flags,
    }

    if args.json:
        print(json.dumps(out, indent=2))
    else:
        severity_label = {"OK": "OK", "WARN": "WARN", "ALERT": "ALERT"}[report.severity]
        print(f"[{severity_label}] Calibration {report.severity} — {args.profile} ({args.window})")
        print(f"  Live:     n={report.live.n}  WR={report.live.wr}%  PF={report.live.pf}  Sharpe={report.live.sharpe}")
        print(f"  Backtest: n={report.backtest.n}  WR={report.backtest.wr}%  PF={report.backtest.pf}  Sharpe={report.backtest.sharpe}")
        print(f"  Drifts:   WR={report.wr_drift_pct:+.1f}%  PF={report.pf_drift_pct:+.1f}%  Sharpe={report.sharpe_drift:+.2f}")
        for f in report.flags:
            print(f"  * {f}")

    # macOS notify
    if args.notify and report.severity in ("ALERT", "WARN"):
        try:
            subprocess.run(
                ["osascript", "-e",
                 f'display notification "Calibration {report.severity}: {len(report.flags)} flag(s)" with title "Wally Trader"'],
                check=False, timeout=5,
            )
        except Exception:
            pass


if __name__ == "__main__":
    main()
