"""Profile-agnostic composite score 0-100 for any asset.

Delegates sub-score computation to hunt.py helpers — single implementation,
two call-sites (hunt.py via score_asset, this module via composite_score).
"""
from __future__ import annotations

from wally_core.hunt import (
    _momentum_score,
    _volatility_score,
    _trend_score,
    _volume_score,
    _MIN_BARS,
)

# Weights mirror hunt.py contract
_WEIGHTS = {
    "momentum": 0.30,
    "volatility": 0.25,
    "trend": 0.25,
    "volume": 0.20,
}


def composite_score(symbol: str, bars: list[dict]) -> int:
    """Compute composite multi-factor score 0-100 for an asset.

    Identical sub-score weighting as hunt.score_asset but profile-agnostic
    (no regime parameter, no ScoreCard — just the integer total).

    Args:
        symbol: asset identifier (part of API contract, unused in math).
        bars: list of OHLCV dicts with keys: open, high, low, close, volume.

    Returns:
        Integer 0-100.

    Raises:
        ValueError: if fewer than _MIN_BARS bars provided.
    """
    if len(bars) < _MIN_BARS:
        raise ValueError(f"Need at least {_MIN_BARS} bars, got {len(bars)}")

    mom = _momentum_score(bars)
    vol = _volatility_score(bars)
    trend = _trend_score(bars)
    volume = _volume_score(bars)

    total = round(
        mom * _WEIGHTS["momentum"]
        + vol * _WEIGHTS["volatility"]
        + trend * _WEIGHTS["trend"]
        + volume * _WEIGHTS["volume"]
    )
    return max(0, min(100, total))
