"""Tests for wally_core.hunt — multi-factor score 0-100 for asset selection."""
import pytest
from wally_core.hunt import score_asset, ScoreCard


# ── Test 1: basic call returns valid ScoreCard ────────────────────────────────

def test_score_asset_returns_scorecard(ohlcv_btc_1h_trending):
    result = score_asset("BTCUSDT", ohlcv_btc_1h_trending, regime="RANGE_CHOP")
    assert isinstance(result, ScoreCard)
    assert 0 <= result.total <= 100
    assert 0 <= result.momentum <= 100
    assert 0 <= result.volatility <= 100
    assert 0 <= result.trend <= 100
    assert 0 <= result.volume <= 100


# ── Test 2: total is weighted sum of sub-scores ───────────────────────────────

def test_score_total_is_weighted_combination(ohlcv_btc_1h_trending):
    result = score_asset("BTCUSDT", ohlcv_btc_1h_trending, regime="RANGE_CHOP")
    expected = (
        result.momentum * 0.30
        + result.volatility * 0.25
        + result.trend * 0.25
        + result.volume * 0.20
    )
    assert abs(result.total - round(expected)) <= 1  # allow rounding epsilon


# ── Test 3: trending fixture scores higher total than flat data ───────────────

def test_trending_fixture_scores_higher_than_flat(ohlcv_btc_1h_trending):
    """Flat bars have no directional momentum, trend, or volume spike."""
    flat_bars = [
        {"time": i * 3600, "open": 70000.0, "high": 70010.0,
         "low": 69990.0, "close": 70000.0, "volume": 100.0}
        for i in range(100)
    ]
    trending_score = score_asset("BTCUSDT", ohlcv_btc_1h_trending, regime="TREND_FUERTE")
    flat_score = score_asset("BTCUSDT", flat_bars, regime="RANGE_CHOP")
    assert trending_score.total > flat_score.total


# ── Test 4: momentum sub-score reflects RSI direction ────────────────────────

def test_momentum_score_higher_when_recent_closes_up(ohlcv_btc_1h_trending):
    """The trending fixture has rising closes, so momentum score should be > 50."""
    result = score_asset("BTCUSDT", ohlcv_btc_1h_trending, regime="TREND_FUERTE")
    assert result.momentum > 50


# ── Test 5: insufficient bars raises ValueError ───────────────────────────────

def test_score_asset_raises_on_too_few_bars():
    tiny = [{"time": i, "open": 100.0, "high": 101.0, "low": 99.0,
              "close": 100.5, "volume": 10.0} for i in range(5)]
    with pytest.raises(ValueError, match="bars"):
        score_asset("BTCUSDT", tiny, regime="RANGE_CHOP")
