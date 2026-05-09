#!/usr/bin/env python3
"""Notion init wizard — interactive guided setup for cross-device memory."""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path


def setup_dashboard_template(api_key: str):
    """Create pre-built widgets in a 'Dashboard' Notion page."""
    print("Creating pre-built dashboard widgets in your Notion workspace...")
    print("   This adds a 'Dashboard' page with embedded views of:")
    print("   - Today's trades (filtered)")
    print("   - Equity curve table")
    print("   - Recent signals")
    print()
    print("   v1: prints SQL-like instructions for manual setup.")
    print("   v2: will auto-create via Notion API.")
    print()
    print("   Manual recipe (paste into Notion page):")
    print("   1. /database, name='Today\\'s Trades', filter date=today")
    print("   2. /linked-database, source=Trades Log, filter date>=last 7d, group by symbol")
    print("   3. /linked-database, source=Equity Curve, sort by date desc, limit 30")
    print()
    print("   See docs/notion-memory-setup.md for layout examples.")


def main():
    import argparse

    p = argparse.ArgumentParser(description="Wally Trader — Notion Memory Setup Wizard")
    p.add_argument("--template", choices=["dashboard"], help="Create pre-built widgets without full wizard")
    args, _ = p.parse_known_args()

    if args.template == "dashboard":
        api_key = os.environ.get("NOTION_API_KEY", "")
        setup_dashboard_template(api_key)
        return 0

    print("=" * 60)
    print("  Wally Trader — Notion Memory Setup Wizard")
    print("=" * 60)
    print()
    print("This wizard helps you activate Notion as cross-device memory backend.")
    print()
    print("Step 1: Get Notion API key")
    print("  Visit: https://www.notion.so/my-integrations")
    print("  Click 'New integration' -> name it 'Wally Trader'")
    print("  Copy the 'Internal Integration Secret' (starts with 'secret_')")
    print()

    api_key = input("Paste your Notion API key (or 'skip' to abort): ").strip()
    if api_key.lower() == "skip" or not api_key.startswith("secret_"):
        print("Aborted. Run again when ready.")
        return 1

    print()
    print("Step 2: Create Notion workspace")
    print("  In Notion, create a new top-level page named 'Wally Trader'")
    print("  Click '...' menu -> 'Add connections' -> select 'Wally Trader' integration")
    print("  This grants the integration access to that page")
    print()
    input("Press ENTER when done...")

    print()
    print("Step 3: Setting environment variable for this shell:")
    bashrc = Path.home() / ".bashrc"
    zshrc = Path.home() / ".zshrc"
    target = zshrc if zshrc.exists() else bashrc
    print(f"  Adding to {target}:")
    print(f"  export NOTION_API_KEY={api_key[:15]}...")

    add_to_rc = input(f"Add to {target.name}? (y/n): ").strip().lower() == "y"
    if add_to_rc:
        with open(target, "a") as f:
            f.write(f"\n# Wally Trader Notion API key\nexport NOTION_API_KEY={api_key}\n")
        print(f"  Added to {target}")

    os.environ["NOTION_API_KEY"] = api_key

    print()
    print("Step 4: Migration of existing local logs to Notion")
    profiles = ["bitunix", "retail", "ftmo", "fundingpips", "fotmarkets", "retail-bingx", "quantfury"]

    print(f"  Profiles available: {', '.join(profiles)}")
    profile = input("  Which profile to migrate first? (default: bitunix): ").strip() or "bitunix"

    confirm = input(f"  Run dry-run migration for {profile}? (y/n): ").strip().lower() == "y"
    if confirm:
        venv = Path("shared/wally_core/.venv/bin/python")
        if not venv.exists():
            print("  Run 'make wally-mcp-install' first to create the venv")
            return 1
        subprocess.run([str(venv), "-m", "wally_core.memory.migrate", "--profile", profile, "--dry-run"], check=True)
        print()
        actually_migrate = input("  Run actual migration (creates Notion DBs)? (y/n): ").strip().lower() == "y"
        if actually_migrate:
            subprocess.run([str(venv), "-m", "wally_core.memory.migrate", "--profile", profile], check=True)

    print()
    print("=" * 60)
    print("  Notion setup complete")
    print()
    print("  Backend default: hybrid (local + Notion async mirror)")
    print("  Cross-device sync: 'make sync-pull PROFILE=<name>' on second device")
    print("  Open Notion app on iPhone to see DBs in real time")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
