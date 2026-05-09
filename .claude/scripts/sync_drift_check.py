#!/usr/bin/env python3
"""Detect clock drift between Mac, Notion server, and (eventual) Hermes Windows."""
import sys
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

_SHARED = Path(__file__).resolve().parent.parent.parent / "shared/wally_core/src"
if _SHARED.exists() and str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from wally_core.ops import detect_clock_drift


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--threshold-seconds", type=int, default=300,
                   help="Alert if abs drift > this (default 300s = 5min)")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    result = detect_clock_drift()

    if args.json:
        result["threshold_seconds"] = args.threshold_seconds
        result["alert"] = result.get("abs_drift_seconds", 0) > args.threshold_seconds
        print(json.dumps(result, indent=2))
        sys.exit(0)

    if result.get("error"):
        print(f"Drift check failed: {result['error']}")
        sys.exit(1)

    abs_drift = result["abs_drift_seconds"]
    if abs_drift > args.threshold_seconds:
        print(f"CLOCK DRIFT: {result['drift_seconds']:+.1f}s vs Cloudflare (>{args.threshold_seconds}s threshold)")
        sys.exit(2)
    elif abs_drift > 30:
        print(f"Mild drift: {result['drift_seconds']:+.1f}s vs Cloudflare")
    else:
        print(f"Clock in sync: {result['drift_seconds']:+.1f}s vs Cloudflare")


if __name__ == "__main__":
    main()
