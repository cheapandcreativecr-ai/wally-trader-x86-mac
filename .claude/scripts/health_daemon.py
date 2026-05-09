#!/usr/bin/env python3
"""Health daemon — runs every 60s, writes health.jsonl, alerts on CRITICAL."""
import sys
import argparse
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

_SHARED = Path(__file__).resolve().parent.parent.parent / "shared/wally_core/src"
if _SHARED.exists() and str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from wally_core.ops import run_all_checks, overall_status


def write_health_log(checks: list, log_path: Path):
    """Append health snapshot to JSONL."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a") as f:
        snapshot = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall": overall_status(checks),
            "checks": [
                {"name": c.name, "status": c.status, "detail": c.detail,
                 "latency_ms": c.latency_ms}
                for c in checks
            ],
        }
        f.write(json.dumps(snapshot) + "\n")


def macos_notify(title: str, body: str):
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{body}" with title "{title}"'],
            check=False, timeout=3,
        )
    except Exception:
        pass


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--once", action="store_true", help="Run a single check and exit")
    p.add_argument("--interval", type=int, default=60, help="Seconds between checks")
    p.add_argument("--log", default="logs/health.jsonl")
    p.add_argument("--notify-on-critical", action="store_true", default=True)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    log_path = Path(args.log)

    while True:
        checks = run_all_checks()
        write_health_log(checks, log_path)

        status = overall_status(checks)
        criticals = [c for c in checks if c.status == "critical"]

        if args.json:
            print(json.dumps({"overall": status, "n_critical": len(criticals)}))
        else:
            emoji = {"ok": "✅", "warn": "⚠️", "critical": "🚨"}[status]
            print(f"{emoji} Health: {status}  | {len(criticals)} critical")
            for c in checks:
                mark = {"ok": "✓", "warn": "!", "critical": "✗"}[c.status]
                print(f"  {mark} {c.name}: {c.detail}")

        if args.notify_on_critical and criticals:
            macos_notify(
                title="Wally Trader CRITICAL",
                body=f"{len(criticals)} critical: " + ", ".join(c.name for c in criticals),
            )

        if args.once:
            sys.exit(0 if status != "critical" else 2)

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
