from __future__ import annotations
import argparse
import os
from .local import LocalBackend
from .notion import NotionBackend


def migrate_profile(profile: str, *, dry_run: bool = True) -> dict:
    """Migrate signals from local CSV to Notion. Idempotent on UUID."""
    local = LocalBackend()
    sigs = list(local.read_signals(profile))
    if dry_run:
        return {"would_migrate": len(sigs), "actually_migrated": 0}
    notion = NotionBackend()
    existing = {s.id for s in notion.read_signals(profile)}
    new = [s for s in sigs if s.id not in existing]
    for s in new:
        notion.append_signal(profile, s)
    return {
        "would_migrate": len(sigs),
        "actually_migrated": len(new),
        "skipped": len(sigs) - len(new),
    }


def rollback_profile(profile: str) -> dict:
    """Export Notion → local CSV. Switches caller back to local backend."""
    notion = NotionBackend()
    local = LocalBackend()
    sigs = list(notion.read_signals(profile))
    for s in sigs:
        local.append_signal(profile, s)
    return {"exported": len(sigs)}


def _cli():
    p = argparse.ArgumentParser()
    p.add_argument("--profile", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--rollback", action="store_true")
    args = p.parse_args()
    if args.rollback:
        print(rollback_profile(args.profile))
    else:
        print(migrate_profile(args.profile, dry_run=args.dry_run))


if __name__ == "__main__":
    _cli()
