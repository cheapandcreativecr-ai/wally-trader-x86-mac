#!/usr/bin/env python3
"""Daily backup of memory/, CSVs, profile configs to ~/wally-backups/."""
import sys
import argparse
import os
import subprocess
import tarfile
from datetime import datetime, timezone
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--retain", type=int, default=14, help="Keep last N backups")
    p.add_argument("--out-dir", default=str(Path.home() / "wally-backups"))
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    archive_path = out_dir / f"wally-backup-{today}.tar.gz"

    # Items to back up
    repo = Path("/Users/josecampos/Documents/wally-trader")
    targets = [
        repo / ".claude/profiles",
        repo / ".claude/cache",
        repo / "logs",
    ]

    print(f"Creating backup: {archive_path}")
    if args.dry_run:
        for t in targets:
            print(f"  - would include {t}")
        sys.exit(0)

    with tarfile.open(archive_path, "w:gz") as tar:
        for t in targets:
            if t.exists():
                tar.add(str(t), arcname=t.relative_to(repo))
                print(f"  + {t.name}")
            else:
                print(f"  skip (missing): {t}")

    # Cleanup old backups
    backups = sorted(out_dir.glob("wally-backup-*.tar.gz"))
    if len(backups) > args.retain:
        for old in backups[:-args.retain]:
            old.unlink()
            print(f"  deleted old backup: {old.name}")

    size_mb = archive_path.stat().st_size / 1024 / 1024
    print(f"Backup complete: {size_mb:.1f}MB | {len(backups)} total")


if __name__ == "__main__":
    main()
