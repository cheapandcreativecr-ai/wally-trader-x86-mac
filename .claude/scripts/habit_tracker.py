#!/usr/bin/env python3
"""Daily habit checklist with streak tracking."""
import sys
import argparse
import json
import os
from datetime import datetime, timezone, date
from pathlib import Path


HABITS = [
    ("morning_protocol", "Did I run /morning before any trade?"),
    ("checklist", "Did I run pre-trade checklist on every trade?"),
    ("journal", "Did I run /journal at end of day?"),
    ("no_revenge", "No trades opened within 30min of a loss?"),
    ("size_within_2pct", "All trades respected 2% capital risk rule?"),
    ("no_override", "No SL was moved against the position?"),
]


def _log_path(profile: str) -> Path:
    base = Path(os.environ.get("WALLY_PROFILES_DIR", ".claude/profiles"))
    return base / profile / "memory" / "habits.jsonl"


def check_in(profile: str, answers: dict, today: date = None) -> dict:
    """Append today's check-in to habits.jsonl."""
    today = today or datetime.now(timezone.utc).date()
    log = _log_path(profile)
    log.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "date": today.isoformat(),
        "profile": profile,
        "answers": answers,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "score_pct": int(sum(1 for v in answers.values() if v) / len(answers) * 100) if answers else 0,
    }

    with open(log, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return entry


def compute_streak(profile: str) -> dict:
    """Compute current streak of perfect days (all habits checked)."""
    log = _log_path(profile)
    if not log.exists():
        return {"streak": 0, "perfect_days": 0, "total_days": 0}

    entries = []
    with open(log) as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except Exception:
                continue

    # Sort by date desc, count consecutive perfect days from today backwards
    entries.sort(key=lambda e: e["date"], reverse=True)
    streak = 0
    perfect_days = 0

    for e in entries:
        if e.get("score_pct", 0) >= 100:
            perfect_days += 1
            if streak == perfect_days - 1:  # consecutive from top
                streak += 1
        else:
            break  # streak broken

    return {"streak": streak, "perfect_days": perfect_days, "total_days": len(entries)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--profile", default=os.environ.get("WALLY_PROFILE", "bitunix"))
    p.add_argument("--check-in", action="store_true", help="Interactive check-in")
    p.add_argument("--streak", action="store_true", help="Show current streak")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    if args.streak:
        result = compute_streak(args.profile)
        if args.json:
            print(json.dumps(result))
        else:
            print(f"Streak: {result['streak']} day(s) perfect")
            print(f"   Perfect days total: {result['perfect_days']}/{result['total_days']}")
        sys.exit(0)

    if args.check_in:
        print("=" * 50)
        print(f"  Daily Habit Check-in — {args.profile}")
        print("=" * 50)
        answers = {}
        for key, question in HABITS:
            ans = input(f"  {question} (y/n): ").strip().lower()
            answers[key] = ans in ("y", "yes", "s", "si")
        entry = check_in(args.profile, answers)
        print(f"\nLogged. Score: {entry['score_pct']}%")
        if args.json:
            print(json.dumps(entry))
        sys.exit(0)

    # Default: show streak summary
    streak = compute_streak(args.profile)
    print(f"Habit streak: {streak['streak']}d  | {streak['perfect_days']}/{streak['total_days']} perfect")


if __name__ == "__main__":
    main()
