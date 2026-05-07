import pytest
from wally_core.regime import compute_adx, label_regime, RegimeLabel


def test_compute_adx_returns_dict_with_required_keys(ohlcv_btc_1h_trending):
    result = compute_adx(ohlcv_btc_1h_trending, length=14)
    assert set(result.keys()) >= {"adx", "plus_di", "minus_di"}
    assert 0 <= result["adx"] <= 100
    assert 0 <= result["plus_di"] <= 100
    assert 0 <= result["minus_di"] <= 100


def test_compute_adx_trending_data_above_25(ohlcv_btc_1h_trending):
    result = compute_adx(ohlcv_btc_1h_trending, length=14)
    assert result["adx"] >= 25, f"Expected trending fixture ADX >= 25, got {result['adx']}"


def test_label_regime_range_when_adx_low():
    label = label_regime(adx=15.0, plus_di=20.0, minus_di=22.0)
    assert label == RegimeLabel.RANGE_CHOP


def test_label_regime_trend_leve_when_adx_in_25_30():
    label = label_regime(adx=27.0, plus_di=30.0, minus_di=18.0)
    assert label == RegimeLabel.TREND_LEVE


def test_label_regime_trend_fuerte_when_adx_in_30_40():
    label = label_regime(adx=35.0, plus_di=32.0, minus_di=18.0)
    assert label == RegimeLabel.TREND_FUERTE


def test_label_regime_trend_extremo_when_adx_above_40():
    label = label_regime(adx=45.0, plus_di=40.0, minus_di=15.0)
    assert label == RegimeLabel.TREND_EXTREMO
