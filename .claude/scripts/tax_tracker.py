#!/usr/bin/env python3
"""Tax tracker — FIFO P&L per profile per year. Output CSV."""
import sys
import argparse
import csv
import os
from datetime import datetime
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--profile", required=True)
    p.add_argument("--year", type=int, default=datetime.now().year)
    p.add_argument("--out-dir", default=None)
    args = p.parse_args()

    profiles_dir = Path(os.environ.get("WALLY_PROFILES_DIR", ".claude/profiles"))
    csv_in = profiles_dir / args.profile / "memory" / "signals_received.csv"

    if not csv_in.exists():
        print(f"⚠️  No signals CSV at {csv_in}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.out_dir) if args.out_dir else (profiles_dir / args.profile / "memory")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"tax_{args.year}.csv"

    rows = []
    with open(csv_in) as f:
        for r in csv.DictReader(f):
            ts = r.get("ts") or r.get("date") or ""
            if str(args.year) not in ts:
                continue
            outcome = (r.get("outcome") or "").upper()
            if not outcome or outcome == "PENDING":
                continue  # only realized
            try:
                pnl = float(r.get("pnl_usd") or 0)
            except ValueError:
                pnl = 0
            rows.append({
                "date": ts[:10] if "T" in ts else ts,
                "symbol": r.get("symbol", "?"),
                "side": r.get("side", "?"),
                "entry": r.get("entry", ""),
                "exit": r.get("exit_price") or r.get("exit", ""),
                "pnl_usd": pnl,
                "outcome": outcome,
                "is_short_term": True,  # Most crypto trades held <1yr
            })

    if not rows:
        print(f"ℹ️  No realized trades for {args.profile} in {args.year}")
        sys.exit(0)

    rows.sort(key=lambda r: r["date"])

    # Aggregate
    total_pnl = sum(r["pnl_usd"] for r in rows)
    wins = [r for r in rows if r["pnl_usd"] > 0]
    losses = [r for r in rows if r["pnl_usd"] < 0]

    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date", "symbol", "side", "entry", "exit", "pnl_usd", "outcome", "is_short_term"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
        # Summary footer
        f.write(f"\n# SUMMARY for {args.profile} {args.year}\n")
        f.write(f"# Total trades: {len(rows)}\n")
        f.write(f"# Total realized P&L: ${total_pnl:+.2f}\n")
        f.write(f"# Wins: {len(wins)} (${sum(r['pnl_usd'] for r in wins):+.2f})\n")
        f.write(f"# Losses: {len(losses)} (${sum(r['pnl_usd'] for r in losses):+.2f})\n")

    print(f"✓ Tax CSV: {out_path}")
    print(f"  {len(rows)} trades, total realized P&L ${total_pnl:+.2f}")


if __name__ == "__main__":
    main()
