#!/usr/bin/env python3
"""Outcome tracking v2 — auto-captures regime+timing+MFE/MAE+lesson tags when closing trades.

Used standalone OR called from existing bitunix_log.py via subprocess.
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "shared/wally_core/src"))


def auto_detect_lesson_tags(*, regime_at_entry: str, regime_at_exit: str, side: str,
                              entry: float, exit: float, max_favorable: float | None,
                              max_adverse: float | None, hold_minutes: int) -> list[str]:
    """Heuristic tagging based on trade pattern."""
    tags = []

    pnl_pct = (entry - exit) / entry * 100 if side == "SHORT" else (exit - entry) / entry * 100

    if pnl_pct > 0:
        tags.append("WIN")
    else:
        tags.append("LOSS")

    # Quick scalp
    if hold_minutes < 15:
        tags.append("scalp")
    elif hold_minutes < 90:
        tags.append("intraday")
    elif hold_minutes < 1440:
        tags.append("session_hold")
    else:
        tags.append("multi_day")

    # Counter-trend detection
    if regime_at_entry in ("TREND_FUERTE", "TREND_EXTREMO"):
        if (side == "SHORT" and "UP" not in regime_at_entry) or \
           (side == "LONG" and "DOWN" not in regime_at_entry):
            pass  # aligned
        else:
            tags.append("counter_trend")

    # Fade-the-pump pattern
    if regime_at_entry == "TREND_EXTREMO" and side == "SHORT" and pnl_pct > 0:
        tags.append("fade_the_pump_WIN")

    # Regime change during trade
    if regime_at_entry != regime_at_exit:
        tags.append(f"regime_changed:{regime_at_entry}>{regime_at_exit}")

    # MFE/MAE analysis
    if max_favorable is not None and max_adverse is not None:
        if pnl_pct < 0 and max_favorable > 0:
            tags.append("gave_back_profit")
        if pnl_pct > 0 and abs(max_adverse) > pnl_pct:
            tags.append("survived_drawdown")

    return tags


def log_outcome_v2(
    *, profile: str, symbol: str, side: str,
    entry: float, exit: float, qty: float,
    open_time_utc: str, close_time_utc: str,
    pnl_usd: float,
    regime_at_entry: str = "UNKNOWN",
    regime_at_exit: str = "UNKNOWN",
    max_favorable_excursion: Optional[float] = None,
    max_adverse_excursion: Optional[float] = None,
    raw_outcome: str = "manual",
    notes: str = "",
):
    """Append a v2 outcome row to .claude/profiles/<profile>/memory/outcomes_v2.csv"""
    profile_dir = Path(os.environ.get("WALLY_PROFILES_DIR", ".claude/profiles")) / profile / "memory"
    profile_dir.mkdir(parents=True, exist_ok=True)
    csv_path = profile_dir / "outcomes_v2.csv"

    open_dt = datetime.fromisoformat(open_time_utc.replace("Z", "+00:00"))
    close_dt = datetime.fromisoformat(close_time_utc.replace("Z", "+00:00"))
    hold_minutes = int((close_dt - open_dt).total_seconds() / 60)

    pnl_pct = (entry - exit) / entry * 100 if side == "SHORT" else (exit - entry) / entry * 100

    tags = auto_detect_lesson_tags(
        regime_at_entry=regime_at_entry, regime_at_exit=regime_at_exit, side=side,
        entry=entry, exit=exit, max_favorable=max_favorable_excursion,
        max_adverse=max_adverse_excursion, hold_minutes=hold_minutes,
    )

    cols = [
        "open_time_utc", "close_time_utc", "hold_minutes",
        "profile", "symbol", "side",
        "entry", "exit", "qty",
        "pnl_usd", "pnl_pct",
        "regime_at_entry", "regime_at_exit",
        "max_favorable_excursion", "max_adverse_excursion",
        "raw_outcome", "lesson_tags", "notes",
    ]

    write_header = not csv_path.exists() or csv_path.stat().st_size == 0
    with open(csv_path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        if write_header:
            w.writeheader()
        w.writerow({
            "open_time_utc": open_time_utc,
            "close_time_utc": close_time_utc,
            "hold_minutes": hold_minutes,
            "profile": profile,
            "symbol": symbol,
            "side": side,
            "entry": entry,
            "exit": exit,
            "qty": qty,
            "pnl_usd": pnl_usd,
            "pnl_pct": round(pnl_pct, 2),
            "regime_at_entry": regime_at_entry,
            "regime_at_exit": regime_at_exit,
            "max_favorable_excursion": max_favorable_excursion or "",
            "max_adverse_excursion": max_adverse_excursion or "",
            "raw_outcome": raw_outcome,
            "lesson_tags": "|".join(tags),
            "notes": notes,
        })

    return {
        "csv_path": str(csv_path),
        "hold_minutes": hold_minutes,
        "pnl_pct": round(pnl_pct, 2),
        "lesson_tags": tags,
    }


def _cli():
    p = argparse.ArgumentParser()
    p.add_argument("--profile", required=True)
    p.add_argument("--symbol", required=True)
    p.add_argument("--side", choices=["LONG", "SHORT"], required=True)
    p.add_argument("--entry", type=float, required=True)
    p.add_argument("--exit", type=float, required=True)
    p.add_argument("--qty", type=float, required=True)
    p.add_argument("--open-time", required=True, help="ISO UTC timestamp")
    p.add_argument("--close-time", default="", help="ISO UTC, defaults to now")
    p.add_argument("--pnl-usd", type=float, required=True)
    p.add_argument("--regime-entry", default="UNKNOWN")
    p.add_argument("--regime-exit", default="UNKNOWN")
    p.add_argument("--mfe", type=float, default=None)
    p.add_argument("--mae", type=float, default=None)
    p.add_argument("--outcome", default="manual")
    p.add_argument("--notes", default="")
    args = p.parse_args()

    close_time = args.close_time or datetime.now(timezone.utc).isoformat()

    res = log_outcome_v2(
        profile=args.profile, symbol=args.symbol, side=args.side,
        entry=args.entry, exit=args.exit, qty=args.qty,
        open_time_utc=args.open_time, close_time_utc=close_time,
        pnl_usd=args.pnl_usd,
        regime_at_entry=args.regime_entry, regime_at_exit=args.regime_exit,
        max_favorable_excursion=args.mfe, max_adverse_excursion=args.mae,
        raw_outcome=args.outcome, notes=args.notes,
    )
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    _cli()
