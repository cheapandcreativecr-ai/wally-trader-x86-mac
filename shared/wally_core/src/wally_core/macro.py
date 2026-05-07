"""Read-only interface for macro events cache.

Writer is .claude/scripts/macro_calendar.py (runs via launchd).
This module only reads. Cache path configurable via WALLY_MACRO_CACHE env var.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

CR_OFFSET = timezone(timedelta(hours=-6))
_DEFAULT_CACHE = Path(__file__).parents[5] / ".claude" / "cache" / "macro_events.json"


def _cache_path() -> Path:
    env = os.environ.get("WALLY_MACRO_CACHE")
    if env:
        return Path(env)
    return _DEFAULT_CACHE


def _load_cache() -> dict[str, Any] | None:
    path = _cache_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict) or "events" not in data:
        return None
    return data


def _event_dt(ev: dict) -> datetime:
    return datetime.fromisoformat(f"{ev['date']}T{ev['time_cr']}:00-06:00")


def is_within_event_window(now: datetime, window_min: int = 30) -> dict:
    """Check if `now` is within ±window_min minutes of any high-impact event.

    Returns:
        {within_event: bool, event: str | None, time_to_event_min: int | None}
    """
    cache = _load_cache()
    if cache is None:
        return {"within_event": False, "event": None, "time_to_event_min": None}

    if now.tzinfo is None:
        now = now.replace(tzinfo=CR_OFFSET)

    high_events = [e for e in cache.get("events", []) if e.get("impact") == "high"]
    for ev in high_events:
        ev_dt = _event_dt(ev)
        delta_min = abs((ev_dt - now).total_seconds()) / 60
        if delta_min <= window_min:
            return {
                "within_event": True,
                "event": ev["name"],
                "time_to_event_min": int(delta_min),
            }
    return {"within_event": False, "event": None, "time_to_event_min": None}


def next_events(days: int = 7, now: datetime | None = None) -> list[dict]:
    """Return upcoming high-impact events within the next `days` days, sorted by time.

    Args:
        days: horizon in days.
        now: override current time (defaults to datetime.now(CR_OFFSET)).
    """
    cache = _load_cache()
    if cache is None:
        return []

    if now is None:
        now = datetime.now(CR_OFFSET)
    if now.tzinfo is None:
        now = now.replace(tzinfo=CR_OFFSET)

    horizon = now + timedelta(days=days)
    upcoming = []
    for ev in cache.get("events", []):
        try:
            ev_dt = _event_dt(ev)
        except (ValueError, KeyError):
            continue
        if now <= ev_dt <= horizon:
            upcoming.append(ev)
    upcoming.sort(key=_event_dt)
    return upcoming
