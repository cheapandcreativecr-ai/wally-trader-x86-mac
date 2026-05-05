"""Shared fixtures for punk_smart tests."""
from datetime import datetime, timezone, timedelta

import pytest

CR_OFFSET = timezone(timedelta(hours=-6))


@pytest.fixture
def tmp_profile_dir(tmp_path, monkeypatch):
    """Provide an isolated profile dir that mimics bitunix layout."""
    profile = tmp_path / "profiles" / "bitunix" / "memory"
    profile.mkdir(parents=True)
    monkeypatch.setenv("WALLY_PROFILE", "bitunix")
    monkeypatch.setenv("WALLY_PROFILE_MEMORY_DIR", str(profile))
    return profile


@pytest.fixture
def cr_time():
    """Build a CR-zoned datetime."""
    def _make(year, month, day, hour=0, minute=0):
        return datetime(year, month, day, hour, minute, tzinfo=CR_OFFSET)
    return _make


@pytest.fixture
def signals_csv_factory(tmp_profile_dir):
    """Write a signals_received.csv with arbitrary rows."""
    csv_path = tmp_profile_dir / "signals_received.csv"
    HEADER = ("date,time,symbol,side,entry,sl,tp,leverage_signal,day_of_week,"
              "filters_4,multifactor,ml_score,chainlink_delta,regime,"
              "pillars_4_count,saturday,verdict,decision,size_pct,executed,"
              "exit_price,exit_reason,pnl_usd,duration_h,hypothetical_outcome,"
              "learning,tier")

    def _write(rows):
        lines = [HEADER]
        for r in rows:
            lines.append(",".join(str(r.get(k, "")) for k in HEADER.split(",")))
        csv_path.write_text("\n".join(lines) + "\n")
        return csv_path
    return _write
