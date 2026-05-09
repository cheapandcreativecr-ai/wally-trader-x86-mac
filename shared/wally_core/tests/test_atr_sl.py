import pytest
from wally_core.atr_sl import volatility_adjusted_sl, auto_tp_levels


def test_volatility_adjusted_sl_long_range_chop():
    res = volatility_adjusted_sl(entry=100.0, side="LONG", atr_pct=1.0, regime="RANGE_CHOP")
    # 1.0% * 1.5 mult = 1.5% SL distance
    assert res["sl_price"] == pytest.approx(98.5, abs=0.01)
    assert res["sl_distance_pct"] == pytest.approx(1.5, abs=0.01)
    assert res["multiplier_used"] == 1.5


def test_volatility_adjusted_sl_short_trend_extremo():
    res = volatility_adjusted_sl(entry=100.0, side="SHORT", atr_pct=2.0, regime="TREND_EXTREMO")
    # 2.0% * 2.5 mult = 5.0% SL distance, SHORT → SL ABOVE
    assert res["sl_price"] == pytest.approx(105.0, abs=0.01)
    assert res["multiplier_used"] == 2.5


def test_auto_tp_levels_long():
    tps = auto_tp_levels(entry=100.0, sl=98.0, side="LONG")
    sl_dist = 2.0
    assert tps["tp1"] == pytest.approx(105.0)  # 2.5R
    assert tps["tp2"] == pytest.approx(108.0)  # 4R
    assert tps["tp3"] == pytest.approx(112.0)  # 6R
    assert tps["tp4"] == pytest.approx(116.0)  # 8R


def test_auto_tp_levels_short():
    tps = auto_tp_levels(entry=100.0, sl=102.0, side="SHORT")
    sl_dist = 2.0
    assert tps["tp1"] == pytest.approx(95.0)
    assert tps["tp2"] == pytest.approx(92.0)
    assert tps["tp3"] == pytest.approx(88.0)
    assert tps["tp4"] == pytest.approx(84.0)


def test_volatility_adjusted_sl_long_trend_fuerte():
    res = volatility_adjusted_sl(entry=50000.0, side="LONG", atr_pct=0.5, regime="TREND_FUERTE")
    # 0.5% * 2.0 = 1.0% SL distance
    assert res["sl_distance_pct"] == pytest.approx(1.0, abs=0.001)
    assert res["multiplier_used"] == 2.0
    assert res["sl_price"] == pytest.approx(49500.0, abs=1.0)


def test_volatility_adjusted_sl_volatile_regime():
    res = volatility_adjusted_sl(entry=100.0, side="SHORT", atr_pct=1.0, regime="VOLATILE")
    # VOLATILE uses 2.5 mult
    assert res["multiplier_used"] == 2.5
    assert res["sl_price"] == pytest.approx(102.5, abs=0.01)


def test_volatility_adjusted_sl_unknown_regime_uses_base():
    res = volatility_adjusted_sl(entry=100.0, side="LONG", atr_pct=1.0,
                                  regime="UNKNOWN", multiplier_base=1.7)
    assert res["multiplier_used"] == 1.7


def test_auto_tp_levels_r_ratios():
    """Verify the R:R ratios are correct for both sides."""
    entry, sl_long = 1000.0, 990.0
    sl_dist = 10.0
    tps = auto_tp_levels(entry=entry, sl=sl_long, side="LONG")
    assert tps["tp1"] == pytest.approx(entry + sl_dist * 2.5)
    assert tps["tp2"] == pytest.approx(entry + sl_dist * 4.0)
    assert tps["tp3"] == pytest.approx(entry + sl_dist * 6.0)
    assert tps["tp4"] == pytest.approx(entry + sl_dist * 8.0)


def test_auto_tp_levels_atr_result_integration():
    """Integration: use atr_sl output as input to auto_tp_levels."""
    sl_data = volatility_adjusted_sl(entry=100.0, side="LONG", atr_pct=1.0)
    tps = auto_tp_levels(entry=100.0, sl=sl_data["sl_price"], side="LONG")
    # sl_price ≈ 98.5, sl_dist ≈ 1.5
    assert tps["tp1"] > 100.0
    assert tps["tp4"] > tps["tp3"] > tps["tp2"] > tps["tp1"]
