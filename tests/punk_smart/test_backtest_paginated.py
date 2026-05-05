"""Tests for paginated Binance fetch."""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".claude" / "scripts"))

import backtest_regime_matrix as bt


def _mock_klines(num_bars: int, start_ts: int = 0):
    """Build a fake Binance klines response."""
    return [[start_ts + i * 900_000, "1.0", "1.5", "0.5", "1.2", "100.0", 0, 0, 0, 0, 0, 0]
            for i in range(num_bars)]


def test_paginated_fetch_returns_all_bars():
    """60d 15m → 5760 bars across 4 calls of 1500 each (last call short)."""
    expected_total = 96 * 60  # 5760

    call_count = {"n": 0}

    def fake_urlopen(req, timeout):
        call_count["n"] += 1
        # Each call returns at most 1500 bars, end-1500 of remaining range
        m = MagicMock()
        if call_count["n"] <= 3:
            payload = _mock_klines(1500, start_ts=call_count["n"] * 1_000_000)
        else:
            payload = _mock_klines(expected_total - 1500 * 3,
                                    start_ts=call_count["n"] * 1_000_000)
        m.read.return_value = bytes(__import__("json").dumps(payload), "utf-8")
        m.__enter__ = lambda s: s
        m.__exit__ = lambda *a: None
        return m

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        bars = bt.fetch_paginated("BTCUSDT", "15m", days=60)

    assert len(bars) == expected_total
    assert call_count["n"] == 4


def test_paginated_dedup_overlap():
    """When pages overlap by 1 bar, output should dedup by timestamp."""
    def fake_urlopen(req, timeout):
        # Always return the same 100-bar payload
        m = MagicMock()
        m.read.return_value = bytes(
            __import__("json").dumps(_mock_klines(100, start_ts=0)), "utf-8")
        m.__enter__ = lambda s: s
        m.__exit__ = lambda *a: None
        return m

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        bars = bt.fetch_paginated("BTCUSDT", "15m", days=1)

    # No duplicate timestamps
    ts = [b["t"] for b in bars]
    assert len(ts) == len(set(ts))
