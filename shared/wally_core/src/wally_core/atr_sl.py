"""Volatility-adjusted SL via ATR percentile."""
from __future__ import annotations
from typing import Literal


def volatility_adjusted_sl(
    entry: float,
    side: Literal["LONG", "SHORT"],
    atr_pct: float,
    regime: str = "RANGE_CHOP",
    multiplier_base: float = 1.5,
) -> dict:
    """Compute SL distance using ATR with regime-aware multiplier.

    Args:
        entry: entry price
        side: LONG or SHORT
        atr_pct: ATR as percentage of price (e.g., 0.5 for 0.5%)
        regime: from regime detector
        multiplier_base: default 1.5 ATR

    Returns dict with sl_price, sl_distance_pct, multiplier_used.
    """
    # Regime-specific multipliers
    regime_mults = {
        "RANGE_CHOP": 1.5,
        "TREND_LEVE": 1.8,
        "TREND_FUERTE": 2.0,
        "TREND_EXTREMO": 2.5,
        "VOLATILE": 2.5,
    }
    mult = regime_mults.get(regime, multiplier_base)

    sl_distance_pct = atr_pct * mult / 100  # convert pct to fraction

    if side == "LONG":
        sl_price = entry * (1 - sl_distance_pct)
    else:
        sl_price = entry * (1 + sl_distance_pct)

    return {
        "sl_price": round(sl_price, 8),
        "sl_distance_pct": round(sl_distance_pct * 100, 3),
        "multiplier_used": mult,
        "regime": regime,
        "atr_pct": atr_pct,
    }


def auto_tp_levels(
    entry: float,
    sl: float,
    side: Literal["LONG", "SHORT"],
) -> dict:
    """Compute 4 staggered TP levels with R:R 2.5/4/6/8."""
    sl_dist = abs(entry - sl)

    if side == "LONG":
        tps = {
            "tp1": entry + sl_dist * 2.5,  # cierre 25%
            "tp2": entry + sl_dist * 4.0,  # cierre 25%
            "tp3": entry + sl_dist * 6.0,  # cierre 25%
            "tp4": entry + sl_dist * 8.0,  # cierre 25% runner
        }
    else:
        tps = {
            "tp1": entry - sl_dist * 2.5,
            "tp2": entry - sl_dist * 4.0,
            "tp3": entry - sl_dist * 6.0,
            "tp4": entry - sl_dist * 8.0,
        }

    return {k: round(v, 8) for k, v in tps.items()}
