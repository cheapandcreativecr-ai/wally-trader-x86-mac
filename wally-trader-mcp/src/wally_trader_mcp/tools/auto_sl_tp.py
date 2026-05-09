"""Auto SL/TP MCP tool wrapper."""
from wally_core.atr_sl import volatility_adjusted_sl, auto_tp_levels


def auto_sl_tp(entry: float, side: str, atr_pct: float, regime: str = "RANGE_CHOP") -> dict:
    """Compute SL + 4 TPs given entry/side/ATR/regime."""
    sl_data = volatility_adjusted_sl(entry, side, atr_pct, regime)
    tps = auto_tp_levels(entry, sl_data["sl_price"], side)
    return {"sl": sl_data, "tps": tps, "entry": entry, "side": side, "regime": regime}
