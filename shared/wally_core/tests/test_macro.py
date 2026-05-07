"""Tests for wally_core.macro — read-only macro events cache interface."""
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

CR_OFFSET = timezone(timedelta(hours=-6))


@pytest.fixture
def macro_cache_file(tmp_path):
    """Synthetic macro_events.json with two events:
    - one 15 min in the future (within ±30 min window)
    - one 4 hours in the future (outside window)
    """
    now = datetime(2026, 5, 7, 9, 0, 0, tzinfo=CR_OFFSET)
    event_near = {
        "name": "CPI m/m",
        "country": "USA",
        "impact": "high",
        "date": "2026-05-07",
        "time_cr": "09:15",
    }
    event_far = {
        "name": "FOMC Statement",
        "country": "USA",
        "impact": "high",
        "date": "2026-05-07",
        "time_cr": "13:00",
    }
    cache = {
        "fetched_at": "2026-05-07T08:00:00-06:00",
        "events": [event_near, event_far],
    }
    f = tmp_path / "macro_events.json"
    f.write_text(json.dumps(cache))
    return f


def set_cache_env(monkeypatch, path: Path):
    monkeypatch.setenv("WALLY_MACRO_CACHE", str(path))


# ── Test 1: within window ──────────────────────────────────────────────────────

def test_is_within_event_window_returns_true_when_15_min_away(monkeypatch, macro_cache_file):
    set_cache_env(monkeypatch, macro_cache_file)
    from wally_core.macro import is_within_event_window
    now = datetime(2026, 5, 7, 9, 0, 0, tzinfo=CR_OFFSET)
    result = is_within_event_window(now, window_min=30)
    assert result["within_event"] is True
    assert "CPI" in result["event"]
    assert result["time_to_event_min"] is not None
    assert result["time_to_event_min"] <= 30


# ── Test 2: outside window ────────────────────────────────────────────────────

def test_is_within_event_window_returns_false_when_4h_away(monkeypatch, macro_cache_file):
    set_cache_env(monkeypatch, macro_cache_file)
    from wally_core.macro import is_within_event_window
    # 9:00 CR — 4h before the far event (13:00), 15 min past the near event (09:15 + already gone)
    now = datetime(2026, 5, 7, 9, 50, 0, tzinfo=CR_OFFSET)
    result = is_within_event_window(now, window_min=30)
    assert result["within_event"] is False
    assert result["event"] is None


# ── Test 3: missing cache → graceful ─────────────────────────────────────────

def test_is_within_event_window_no_cache_returns_not_blocked(monkeypatch, tmp_path):
    monkeypatch.setenv("WALLY_MACRO_CACHE", str(tmp_path / "nonexistent.json"))
    from wally_core.macro import is_within_event_window
    now = datetime(2026, 5, 7, 9, 0, 0, tzinfo=CR_OFFSET)
    result = is_within_event_window(now)
    assert result["within_event"] is False


# ── Test 4: next_events returns sorted list ───────────────────────────────────

def test_next_events_returns_events_within_horizon(monkeypatch, macro_cache_file):
    set_cache_env(monkeypatch, macro_cache_file)
    from wally_core.macro import next_events
    now = datetime(2026, 5, 7, 8, 0, 0, tzinfo=CR_OFFSET)
    events = next_events(days=1, now=now)
    assert len(events) == 2
    # Should be sorted by time
    assert events[0]["time_cr"] < events[1]["time_cr"]


# ── Test 5: next_events empty when no cache ───────────────────────────────────

def test_next_events_empty_when_no_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("WALLY_MACRO_CACHE", str(tmp_path / "nonexistent.json"))
    from wally_core.macro import next_events
    now = datetime(2026, 5, 7, 8, 0, 0, tzinfo=CR_OFFSET)
    events = next_events(days=7, now=now)
    assert events == []
