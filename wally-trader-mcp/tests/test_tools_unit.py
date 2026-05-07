"""In-process unit tests for tool functions (no subprocess MCP needed)."""
import json
import pytest
from pathlib import Path

from wally_trader_mcp.tools.detect_regime import detect_regime
from wally_trader_mcp.tools.validate_setup import validate_setup
from wally_trader_mcp.tools.calculate_risk import calculate_risk
from wally_trader_mcp.tools.multifactor_score import multifactor_score
from wally_trader_mcp.tools.macro_gate_check import macro_gate_check

REPO = Path(__file__).resolve().parent.parent.parent
TRENDING_BARS = REPO / "shared/wally_core/tests/fixtures/btc_1h_trending.json"
RANGE_BARS = REPO / "shared/wally_core/tests/fixtures/btc_15m_range.json"


def test_detect_regime_trending():
    res = detect_regime(str(TRENDING_BARS), length=14)
    assert "adx" in res and "label" in res
    assert res["adx"] >= 25
    assert res["label"] in ("TREND_LEVE", "TREND_FUERTE", "TREND_EXTREMO")


def test_detect_regime_range():
    res = detect_regime(str(RANGE_BARS), length=14)
    assert res["label"] == "RANGE_CHOP"


def test_validate_setup_returns_filters():
    res = validate_setup(str(RANGE_BARS), side="LONG", donchian_length=15)
    assert "go" in res and "filters" in res
    assert len(res["filters"]) == 4


def test_calculate_risk_flat_2pct_basic():
    res = calculate_risk(
        profile="bitunix",
        capital_usd=200,
        entry=68000,
        sl=67500,
        side="LONG",
        leverage=10,
        mode="flat_2pct",
    )
    assert res["risk_usd"] == pytest.approx(4.0)
    assert "leverage_used" in res


def test_calculate_risk_caps_leverage_retail():
    res = calculate_risk(
        profile="retail",
        capital_usd=20,
        entry=68000,
        sl=67500,
        side="LONG",
        leverage=20,
        mode="flat_2pct",
    )
    assert res["leverage_used"] == 10
    assert any("capped" in w for w in res["warnings"])


def test_multifactor_score_returns_score():
    res = multifactor_score("BTC", str(TRENDING_BARS))
    assert "symbol" in res
    assert "score" in res
    assert 0 <= res["score"] <= 100


def test_macro_gate_check_returns_dict(monkeypatch, tmp_path):
    # Use empty cache so result is "no event"
    cache = tmp_path / "macro.json"
    cache.write_text('{"events": []}')
    monkeypatch.setenv("WALLY_MACRO_CACHE", str(cache))
    res = macro_gate_check(window_min=30)
    assert isinstance(res, dict)
    assert "within_event" in res
    assert res["within_event"] is False
