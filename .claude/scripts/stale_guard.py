#!/usr/bin/env python3
"""Reject signals older than N minutes."""
import sys
import argparse
import json
from datetime import datetime, timezone


def is_stale(signal_ts_iso: str, max_age_min: int = 10) -> dict:
    """Check if signal timestamp is older than max_age_min."""
    try:
        signal_ts = datetime.fromisoformat(signal_ts_iso.replace("Z", "+00:00"))
    except Exception as e:
        return {"stale": True, "reason": f"invalid_timestamp: {e}", "age_min": None}

    now = datetime.now(timezone.utc)
    age_seconds = (now - signal_ts).total_seconds()
    age_min = age_seconds / 60

    return {
        "stale": age_min > max_age_min,
        "age_min": round(age_min, 2),
        "max_age_min": max_age_min,
        "reason": f"signal_age_{age_min:.1f}min" if age_min > max_age_min else "ok",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ts", required=True, help="Signal timestamp ISO")
    p.add_argument("--max-age", type=int, default=10)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    result = is_stale(args.ts, args.max_age)
    if args.json:
        print(json.dumps(result))
    else:
        if result["stale"]:
            print(f"STALE: signal age {result['age_min']}min > {result['max_age_min']}min limit")
        else:
            print(f"FRESH: signal age {result['age_min']}min")
    sys.exit(0 if not result["stale"] else 1)


if __name__ == "__main__":
    main()
