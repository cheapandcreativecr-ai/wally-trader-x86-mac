import pytest
from wally_core.risk import calculate_position_size, RiskMode, ProfileLeverageCap


def test_flat_2pct_basic_long():
    result = calculate_position_size(
        capital_usd=200.0,
        entry=68000,
        sl=67500,
        side="LONG",
        leverage=10,
        mode=RiskMode.FLAT_2PCT,
        profile="bitunix",
    )
    assert result.risk_usd == pytest.approx(4.0)
    assert result.position_size_btc > 0


def test_flat_2pct_respects_leverage_cap_retail_10x():
    result = calculate_position_size(
        capital_usd=20.0, entry=68000, sl=67500, side="LONG",
        leverage=20,
        mode=RiskMode.FLAT_2PCT, profile="retail",
    )
    assert result.leverage_used == 10


def test_flat_2pct_respects_leverage_cap_bitunix_20x():
    result = calculate_position_size(
        capital_usd=200.0, entry=68000, sl=67500, side="LONG",
        leverage=25,
        mode=RiskMode.FLAT_2PCT, profile="bitunix",
    )
    assert result.leverage_used == 20
    assert "WARN" in result.warnings[0]


def test_var_mode_sizing_uses_atr_percentile(ohlcv_btc_15m_range):
    result = calculate_position_size(
        capital_usd=200.0, entry=68000, sl=67500, side="LONG",
        leverage=10, mode=RiskMode.VAR, profile="bitunix",
        bars_for_var=ohlcv_btc_15m_range,
    )
    assert result.risk_usd <= 4.0
    assert result.var_pct is not None


def test_parity_mode_requires_assets_dict():
    with pytest.raises(ValueError, match="parity"):
        calculate_position_size(
            capital_usd=10000, entry=1.10, sl=1.095, side="LONG",
            leverage=50, mode=RiskMode.PARITY, profile="ftmo",
        )


def test_auto_levels_combines_leverage_cap_and_atr_sl():
    from wally_core.risk import auto_levels
    res = auto_levels(
        entry=100.0, side="LONG", atr_pct=1.0,
        regime="RANGE_CHOP", profile="bitunix", leverage=25,
    )
    assert res["leverage_used"] == 20  # capped from 25 → 20
    assert len(res["warnings"]) > 0
    assert "WARN" in res["warnings"][0]
    assert res["sl"]["sl_price"] == pytest.approx(98.5, abs=0.01)
    assert "tp1" in res["tps"]


def test_auto_levels_no_cap_warning_when_under_cap():
    from wally_core.risk import auto_levels
    res = auto_levels(
        entry=50000.0, side="SHORT", atr_pct=0.5,
        regime="TREND_FUERTE", profile="retail", leverage=5,
    )
    assert res["leverage_used"] == 5
    assert res["warnings"] == []
    assert res["sl"]["multiplier_used"] == 2.0


def test_auto_levels_unknown_profile_defaults_10x():
    from wally_core.risk import auto_levels
    res = auto_levels(
        entry=100.0, side="LONG", atr_pct=1.0,
        regime="RANGE_CHOP", profile="unknown_profile", leverage=15,
    )
    assert res["leverage_used"] == 10
    assert "WARN" in res["warnings"][0]
