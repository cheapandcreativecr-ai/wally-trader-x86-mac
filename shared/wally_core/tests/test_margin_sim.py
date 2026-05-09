import sys
import importlib.util
import pytest
from pathlib import Path

# Import directly from file to avoid triggering wally_trader_mcp.__init__ (which needs mcp package)
_tool_path = Path(__file__).resolve().parent.parent.parent.parent / "wally-trader-mcp/src/wally_trader_mcp/tools/margin_sim.py"
_spec = importlib.util.spec_from_file_location("margin_sim_mod", _tool_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
margin_sim = _mod.margin_sim


def test_margin_sim_long_10x():
    res = margin_sim(entry=100.0, leverage=10, side="LONG")
    assert res["initial_margin_pct"] == 10.0
    assert res["liq_buffer_pct"] == 9.5
    # LONG → liq is below entry
    assert res["liq_price"] == pytest.approx(90.5, abs=0.01)


def test_margin_sim_short_5x():
    res = margin_sim(entry=100.0, leverage=5, side="SHORT")
    # 5x → 20% margin, 19.5% buffer
    assert res["liq_buffer_pct"] == 19.5
    # SHORT → liq is above entry
    assert res["liq_price"] == pytest.approx(119.5, abs=0.01)


def test_margin_sim_table_includes_liquidation():
    res = margin_sim(entry=100.0, leverage=20, side="LONG")
    # 20x → 5% margin, 4.5% buffer → 5% adverse hits LIQ
    table = res["table"]
    assert any(t.get("result") == "LIQUIDATION" for t in table)


def test_margin_sim_keys_present():
    res = margin_sim(entry=50000.0, leverage=10, side="LONG")
    for key in ["entry", "side", "leverage", "initial_margin_pct", "liq_buffer_pct", "liq_price", "table"]:
        assert key in res


def test_margin_sim_short_liq_above_entry():
    res = margin_sim(entry=50000.0, leverage=10, side="SHORT")
    assert res["liq_price"] > res["entry"]


def test_margin_sim_long_liq_below_entry():
    res = margin_sim(entry=50000.0, leverage=10, side="LONG")
    assert res["liq_price"] < res["entry"]
