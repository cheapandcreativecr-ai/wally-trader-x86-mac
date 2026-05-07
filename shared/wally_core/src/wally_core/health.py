"""System health check for wally_core.

Checks:
  - macro_cache_age_hours: how old is the macro events cache (None if missing)
  - profile_valid: WALLY_PROFILE env is a known profile
  - locks_free: no stale .lock files in profiles/*/memory/ (>60s old)
  - ok: True if profile_valid and locks_free (cache age is informational only)

No MCP checks here — those live in wally-trader-mcp/server.py.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

CR_OFFSET = timezone(timedelta(hours=-6))

KNOWN_PROFILES = frozenset([
    "retail",
    "retail-bingx",
    "ftmo",
    "fundingpips",
    "fotmarkets",
    "bitunix",
    "quantfury",
])

_STALE_LOCK_SECONDS = 60


@dataclass
class HealthReport:
    macro_cache_age_hours: Optional[float]  # None if cache missing
    profile_valid: bool
    locks_free: bool
    ok: bool  # True iff profile_valid AND locks_free


def _macro_cache_age_hours() -> Optional[float]:
    """Return age of macro events cache in hours, or None if missing/unreadable."""
    cache_path_str = os.environ.get("WALLY_MACRO_CACHE")
    if cache_path_str:
        cache_path = Path(cache_path_str)
    else:
        # Default path relative to package (5 parents up from this file)
        cache_path = Path(__file__).parents[5] / ".claude" / "cache" / "macro_events.json"

    if not cache_path.exists():
        return None
    try:
        data = json.loads(cache_path.read_text())
        fetched_at_str = data.get("fetched_at")
        if not fetched_at_str:
            return None
        fetched_at = datetime.fromisoformat(fetched_at_str)
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=CR_OFFSET)
        now = datetime.now(CR_OFFSET)
        return (now - fetched_at).total_seconds() / 3600
    except (json.JSONDecodeError, OSError, ValueError):
        return None


def _profile_valid() -> bool:
    """Return True if WALLY_PROFILE env is a known profile."""
    profile = os.environ.get("WALLY_PROFILE", "")
    return profile in KNOWN_PROFILES


def _locks_free() -> bool:
    """Return False if any .lock files in profiles/*/memory/ are older than 60s."""
    profiles_dir_str = os.environ.get("WALLY_PROFILES_DIR")
    if profiles_dir_str:
        profiles_dir = Path(profiles_dir_str)
    else:
        profiles_dir = Path(__file__).parents[5] / ".claude" / "profiles"

    if not profiles_dir.exists():
        return True  # No profiles dir → nothing to check

    now = time.time()
    for lock_file in profiles_dir.glob("*/memory/*.lock"):
        try:
            age = now - lock_file.stat().st_mtime
            if age > _STALE_LOCK_SECONDS:
                return False
        except OSError:
            continue
    return True


def health_check() -> HealthReport:
    """Run all sub-checks and return a HealthReport.

    ok = profile_valid AND locks_free
    (macro cache age is informational — absence is not critical)
    """
    cache_age = _macro_cache_age_hours()
    profile_ok = _profile_valid()
    locks_ok = _locks_free()
    overall = profile_ok and locks_ok

    return HealthReport(
        macro_cache_age_hours=round(cache_age, 2) if cache_age is not None else None,
        profile_valid=profile_ok,
        locks_free=locks_ok,
        ok=overall,
    )
