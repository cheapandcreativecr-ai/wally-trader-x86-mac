import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / ".claude/scripts"))

from stale_guard import is_stale


def test_fresh_signal():
    ts = datetime.now(timezone.utc).isoformat()
    res = is_stale(ts, max_age_min=10)
    assert not res["stale"]
    assert res["age_min"] < 1


def test_stale_signal():
    ts = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
    res = is_stale(ts, max_age_min=10)
    assert res["stale"]
    assert res["age_min"] > 10


def test_invalid_ts():
    res = is_stale("not-a-timestamp", max_age_min=10)
    assert res["stale"]
    assert "invalid_timestamp" in res["reason"]


def test_exactly_at_limit():
    # 10 minutes = 600 seconds; we test something just under the limit
    ts = (datetime.now(timezone.utc) - timedelta(minutes=9, seconds=59)).isoformat()
    res = is_stale(ts, max_age_min=10)
    assert not res["stale"]


def test_just_over_limit():
    ts = (datetime.now(timezone.utc) - timedelta(minutes=10, seconds=1)).isoformat()
    res = is_stale(ts, max_age_min=10)
    assert res["stale"]


def test_custom_max_age():
    ts = (datetime.now(timezone.utc) - timedelta(minutes=25)).isoformat()
    # 30min limit — should be fresh
    res = is_stale(ts, max_age_min=30)
    assert not res["stale"]
    # 20min limit — should be stale
    res2 = is_stale(ts, max_age_min=20)
    assert res2["stale"]


def test_future_timestamp():
    # Future timestamps should be "fresh" (age_min < 0 but not > max_age)
    ts = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    res = is_stale(ts, max_age_min=10)
    assert not res["stale"]


def test_z_suffix_handled():
    ts = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    res = is_stale(ts, max_age_min=10)
    assert not res["stale"]


def test_reason_ok_when_fresh():
    ts = datetime.now(timezone.utc).isoformat()
    res = is_stale(ts, max_age_min=10)
    assert res["reason"] == "ok"


def test_reason_contains_age_when_stale():
    ts = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()
    res = is_stale(ts, max_age_min=10)
    assert "signal_age_" in res["reason"]
