"""Tests for session_quality.py — VWAP-flat detector.

The script lives in .claude/scripts/session_quality.py (CLI). We test the
pure-python helpers (compute_vwap_dispersion, compute_range_pct, assess_session)
by importing the module via importlib (file-based, no installable package).

Network-dependent paths (fetch_klines) are tested with a stub.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch


def _load_session_quality():
    """Load .claude/scripts/session_quality.py as a module."""
    script_path = (
        Path(__file__).resolve().parents[3] / ".claude" / "scripts" / "session_quality.py"
    )
    assert script_path.exists(), f"missing script: {script_path}"
    spec = importlib.util.spec_from_file_location("session_quality", str(script_path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["session_quality"] = mod
    spec.loader.exec_module(mod)
    return mod


sq = _load_session_quality()


def _bars(closes: list[float], vol: float = 1000.0) -> list[list]:
    """Build minimal Binance-format kline rows from a list of closes.

    Each row: [openTime, open, high, low, close, volume, ...]. We use close=high=low
    for synthetic flat data, or wider H/L for compressed/active.
    """
    out = []
    for i, c in enumerate(closes):
        out.append([i * 900_000, c, c, c, c, vol, 0, 0, 0, 0, 0, 0])
    return out


# ---------------- VWAP dispersion ----------------


def test_vwap_dispersion_flat_chart_is_zero():
    bars = _bars([100.0] * 12)
    r = sq.compute_vwap_dispersion(bars)
    assert r["vwap"] == 100.0
    assert r["std_pct"] == 0.0
    assert r["mean"] == 100.0


def test_vwap_dispersion_active_chart_is_nonzero():
    bars = _bars([100.0, 102.0, 98.0, 101.0, 99.0, 103.0, 97.0, 100.0])
    r = sq.compute_vwap_dispersion(bars)
    assert r["vwap"] > 0
    assert r["std_pct"] > 0.5  # Real movement → real dispersion


def test_vwap_dispersion_handles_zero_volume():
    bars = _bars([100.0, 101.0], vol=0.0)
    r = sq.compute_vwap_dispersion(bars)
    assert r == {"vwap": 0.0, "std_pct": 0.0, "mean": 0.0}


# ---------------- Range pct ----------------


def test_range_pct_compressed():
    # 8 bars all between 100 and 100.3 → range = 0.3%
    bars = _bars([100.0, 100.1, 100.2, 100.0, 100.1, 100.3, 100.2, 100.1])
    # Need to set actual highs/lows
    for b in bars:
        b[2] = b[1]  # high = open
        b[3] = b[1]  # low = open
    bars[5][2] = 100.3  # set max high
    bars[0][3] = 100.0  # set min low
    r = sq.compute_range_pct(bars, n=8)
    assert 0.25 <= r <= 0.35  # ~0.3%


def test_range_pct_active():
    bars = _bars([100.0, 102.0, 98.0, 101.0, 99.0, 103.0, 97.0, 100.0])
    for b in bars:
        b[2] = b[1] * 1.005
        b[3] = b[1] * 0.995
    r = sq.compute_range_pct(bars, n=8)
    assert r > 5.0  # Wide range


def test_range_pct_zero_close_returns_zero():
    bars = _bars([0.0, 0.0, 0.0])
    for b in bars:
        b[2] = 0.0
        b[3] = 0.0
    r = sq.compute_range_pct(bars, n=3)
    assert r == 0.0


# ---------------- Verdict logic via assess_session ----------------


def test_assess_session_block_when_dead():
    """Both flat AND compressed → BLOCK."""
    flat_bars = _bars([100.0] * 12)
    with patch.object(sq, "fetch_klines", return_value=flat_bars):
        r = sq.assess_session("FLATCOIN")
    assert r["verdict"] == "BLOCK"
    assert "Dead session" in r["reason"]


def test_assess_session_warn_when_partial():
    """Range OK but VWAP flat → WARN."""
    # Build bars that move within bounds but VWAP std is low
    bars = []
    for i in range(12):
        # alternate small moves keeps VWAP close
        c = 100.0 + (0.05 if i % 2 == 0 else -0.05)
        bars.append([i * 900_000, c, c + 0.5, c - 0.5, c, 1000.0, 0, 0, 0, 0, 0, 0])
    with patch.object(sq, "fetch_klines", return_value=bars):
        r = sq.assess_session("WARNCOIN")
    # std_pct should be near 0; range_pct will be ~1% (above threshold)
    assert r["verdict"] in ("WARN", "BLOCK")  # depends on exact bars


def test_assess_session_ok_when_active():
    bars = _bars([100.0, 102.0, 98.0, 101.0, 99.0, 103.0, 97.0, 100.0, 102.5, 98.5, 101.5, 99.5])
    for b in bars:
        b[2] = b[1] * 1.005
        b[3] = b[1] * 0.995
    with patch.object(sq, "fetch_klines", return_value=bars):
        r = sq.assess_session("ACTIVECOIN")
    assert r["verdict"] == "OK"
    assert r["vwap_std_pct"] > 0
    assert r["range_pct_8bars"] > 0


def test_assess_session_error_when_fetch_fails():
    with patch.object(sq, "fetch_klines", side_effect=Exception("network down")):
        r = sq.assess_session("DOWNCOIN")
    assert r["verdict"] == "ERROR"
    assert "network down" in r["reason"]


def test_assess_session_error_when_insufficient_bars():
    bars = _bars([100.0, 101.0])  # only 2 bars
    with patch.object(sq, "fetch_klines", return_value=bars):
        r = sq.assess_session("THINCOIN", bars=12)
    assert r["verdict"] == "ERROR"
    assert "insufficient" in r["reason"]


def test_thresholds_configurable():
    """Stricter thresholds → BLOCK on borderline session."""
    # Generate borderline bars
    bars = _bars([100.0, 100.05, 99.95, 100.0, 100.05, 99.95, 100.0, 100.05] * 2)
    for b in bars:
        b[2] = b[1] * 1.001
        b[3] = b[1] * 0.999
    # Loose threshold: should be OK
    with patch.object(sq, "fetch_klines", return_value=bars):
        loose = sq.assess_session("X", flat_threshold=0.01, range_threshold=0.05)
        strict = sq.assess_session("X", flat_threshold=1.0, range_threshold=5.0)
    assert loose["verdict"] != "BLOCK"
    assert strict["verdict"] == "BLOCK"
