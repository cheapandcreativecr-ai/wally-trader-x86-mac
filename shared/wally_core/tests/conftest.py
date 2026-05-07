import json
from pathlib import Path
import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"

@pytest.fixture
def ohlcv_btc_15m_range():
    """100 bars of BTC 15m in a range regime (Apr 2026 fixture)."""
    return json.loads((FIXTURES_DIR / "btc_15m_range.json").read_text())

@pytest.fixture
def ohlcv_btc_1h_trending():
    """200 bars of BTC 1h in a trending regime (Mar 2026 fixture)."""
    return json.loads((FIXTURES_DIR / "btc_1h_trending.json").read_text())

@pytest.fixture
def tmp_profile(tmp_path):
    """Temp profile directory mimicking .claude/profiles/<name>/memory/."""
    p = tmp_path / "profiles" / "test_profile" / "memory"
    p.mkdir(parents=True)
    return p
