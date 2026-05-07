"""Tests for wally_core.health — system health check."""
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

CR_OFFSET = timezone(timedelta(hours=-6))

KNOWN_PROFILES = [
    "retail", "retail-bingx", "ftmo", "fundingpips",
    "fotmarkets", "bitunix", "quantfury",
]


@pytest.fixture
def clean_env(monkeypatch, tmp_path):
    """Provide a clean environment with:
    - valid WALLY_PROFILE
    - fresh WALLY_MACRO_CACHE
    - WALLY_PROFILES_DIR pointing to tmp_path (no locks)
    """
    # Valid profile
    monkeypatch.setenv("WALLY_PROFILE", "retail")

    # Fresh macro cache (fetched 1 hour ago)
    cache_file = tmp_path / "macro_events.json"
    fetched_at = (datetime.now(CR_OFFSET) - timedelta(hours=1)).isoformat()
    cache_file.write_text(json.dumps({"fetched_at": fetched_at, "events": []}))
    monkeypatch.setenv("WALLY_MACRO_CACHE", str(cache_file))

    # Empty profiles dir (no locks)
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(profiles_dir))

    return tmp_path


# ── Test 1: clean state returns ok=True ──────────────────────────────────────

def test_clean_state_returns_ok(clean_env):
    from wally_core.health import health_check
    report = health_check()
    assert report.ok is True
    assert report.profile_valid is True
    assert report.locks_free is True


# ── Test 2: invalid profile returns profile_valid=False, ok=False ─────────────

def test_invalid_profile_name(monkeypatch, tmp_path):
    monkeypatch.setenv("WALLY_PROFILE", "not_a_real_profile")
    monkeypatch.setenv("WALLY_MACRO_CACHE", str(tmp_path / "nonexistent.json"))
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(tmp_path / "profiles"))
    (tmp_path / "profiles").mkdir()
    from wally_core.health import health_check
    report = health_check()
    assert report.profile_valid is False
    assert report.ok is False


# ── Test 3: stale lock detected returns locks_free=False, ok=False ─────────────

def test_stale_lock_detected(monkeypatch, tmp_path):
    monkeypatch.setenv("WALLY_PROFILE", "retail")
    cache_file = tmp_path / "macro_events.json"
    fetched_at = (datetime.now(CR_OFFSET) - timedelta(hours=1)).isoformat()
    cache_file.write_text(json.dumps({"fetched_at": fetched_at, "events": []}))
    monkeypatch.setenv("WALLY_MACRO_CACHE", str(cache_file))

    # Create a stale lock (>60 seconds old) by backdating mtime
    profiles_dir = tmp_path / "profiles"
    lock_dir = profiles_dir / "retail" / "memory"
    lock_dir.mkdir(parents=True)
    lock_file = lock_dir / "trading_log.csv.lock"
    lock_file.write_text("99999")  # fake PID that doesn't exist
    # Backdate the lock file to 120 seconds ago
    stale_time = time.time() - 120
    os.utime(lock_file, (stale_time, stale_time))

    monkeypatch.setenv("WALLY_PROFILES_DIR", str(profiles_dir))

    from wally_core.health import health_check
    report = health_check()
    assert report.locks_free is False
    assert report.ok is False


# ── Test 4: missing macro cache → age=None, ok still True ────────────────────

def test_missing_macro_cache_ok(monkeypatch, tmp_path):
    monkeypatch.setenv("WALLY_PROFILE", "bitunix")
    monkeypatch.setenv("WALLY_MACRO_CACHE", str(tmp_path / "nonexistent.json"))
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(profiles_dir))

    from wally_core.health import health_check
    report = health_check()
    assert report.macro_cache_age_hours is None
    # Cache absence is not critical
    assert report.ok is True
