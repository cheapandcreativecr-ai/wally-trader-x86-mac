"""Multi-factor asset scoring for bitunix asset selection.

Exposes score_asset() returning a ScoreCard(0-100 total + 4 sub-scores).

Sub-score helpers are private module-level functions shared with multifactor.py
via direct import (YAGNI: 2 call-sites → factor out once, not a base class).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

_MIN_BARS = 30  # minimum bars required


@dataclass
class ScoreCard:
    total: int       # 0-100 weighted composite
    momentum: int    # 0-100  weight=30%
    volatility: int  # 0-100  weight=25%  (low ATR percentile = higher score)
    trend: int       # 0-100  weight=25%
    volume: int      # 0-100  weight=20%


# ── Private helpers ────────────────────────────────────────────────────────────

def _calc_ema(closes: list[float], period: int) -> list[float]:
    """Exponential moving average — returns same-length list (initial values = sma)."""
    if not closes:
        return []
    k = 2 / (period + 1)
    emas = [closes[0]]
    for c in closes[1:]:
        emas.append(c * k + emas[-1] * (1 - k))
    return emas


def _calc_rsi(closes: list[float], period: int = 14) -> float:
    """RSI(period) over the closes. Returns value 0-100."""
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0.0))
        losses.append(max(-diff, 0.0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def _calc_atr(bars: list[dict], period: int = 14) -> list[float]:
    """Average True Range — returns list of ATR values (length = len(bars) - 1)."""
    trs = []
    for i in range(1, len(bars)):
        h, l, pc = float(bars[i]["high"]), float(bars[i]["low"]), float(bars[i - 1]["close"])
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    if not trs:
        return []
    atrs = [sum(trs[:period]) / period] if len(trs) >= period else [sum(trs) / len(trs)]
    for tr in trs[period:]:
        atrs.append((atrs[-1] * (period - 1) + tr) / period)
    return atrs


def _momentum_score(bars: list[dict]) -> int:
    """0-100: based on RSI(14) and recent close direction.

    RSI 50-100 → higher momentum (long bias). RSI 0-50 → lower.
    Blended with recent 5-bar direction.
    """
    closes = [float(b["close"]) for b in bars]
    rsi = _calc_rsi(closes)
    # RSI component: map 0-100 RSI to 0-100 score
    rsi_score = rsi  # RSI=70 → 70 pts

    # Direction component: recent 5 bars avg vs prior 5 bars avg
    if len(closes) >= 10:
        recent_avg = sum(closes[-5:]) / 5
        prior_avg = sum(closes[-10:-5]) / 5
        if prior_avg > 0:
            chg = (recent_avg - prior_avg) / prior_avg * 100
            # +2% → near 100, -2% → near 0, flat → 50
            dir_score = max(0.0, min(100.0, 50.0 + chg * 25))
        else:
            dir_score = 50.0
    else:
        dir_score = 50.0

    return round(rsi_score * 0.6 + dir_score * 0.4)


def _volatility_score(bars: list[dict]) -> int:
    """0-100: lower ATR percentile → higher score (calmer = better entry conditions)."""
    atrs = _calc_atr(bars)
    if len(atrs) < 2:
        return 50
    current_atr = atrs[-1]
    # Percentile rank of current ATR vs all computed ATRs
    rank = sum(1 for a in atrs if a <= current_atr) / len(atrs)
    # Invert: low ATR percentile → high score
    return round((1.0 - rank) * 100)


def _trend_score(bars: list[dict]) -> int:
    """0-100: EMA(9) vs EMA(21) alignment.

    EMA9 > EMA21 → bullish alignment → higher score.
    Score is based on magnitude of the gap.
    """
    closes = [float(b["close"]) for b in bars]
    if len(closes) < 22:
        return 50
    ema9 = _calc_ema(closes, 9)
    ema21 = _calc_ema(closes, 21)
    last_close = closes[-1]
    if last_close == 0:
        return 50
    gap_pct = (ema9[-1] - ema21[-1]) / last_close * 100
    # Map: +0.5% → ~75, -0.5% → ~25, ±2% → 100/0
    score = 50.0 + gap_pct * 25
    return round(max(0.0, min(100.0, score)))


def _volume_score(bars: list[dict]) -> int:
    """0-100: recent volume vs average ratio.

    Recent 3-bar avg vs overall avg.
    Ratio >= 2x → 100, ratio <= 0.5x → 0, ratio = 1 → 50.
    """
    volumes = [float(b["volume"]) for b in bars]
    if len(volumes) < 10:
        return 50
    avg = sum(volumes[:-3]) / max(len(volumes) - 3, 1)
    recent_avg = sum(volumes[-3:]) / 3
    if avg == 0:
        return 50
    ratio = recent_avg / avg
    # log-linear: ratio=2 → ~100, ratio=0.5 → ~0, ratio=1 → 50
    import math
    score = 50.0 + math.log2(ratio) * 50
    return round(max(0.0, min(100.0, score)))


# ── Public API ─────────────────────────────────────────────────────────────────

def score_asset(symbol: str, bars: list[dict], regime: str) -> ScoreCard:
    """Compute a ScoreCard for an asset based on recent OHLCV bars and regime.

    Args:
        symbol: asset identifier (unused in computation, part of API contract).
        bars: list of OHLCV dicts with keys: open, high, low, close, volume.
        regime: current regime label string (unused in scoring, part of API contract).

    Returns:
        ScoreCard with total 0-100 and 4 sub-scores.

    Raises:
        ValueError: if fewer than _MIN_BARS bars provided.
    """
    if len(bars) < _MIN_BARS:
        raise ValueError(f"Need at least {_MIN_BARS} bars, got {len(bars)}")

    mom = _momentum_score(bars)
    vol = _volatility_score(bars)
    trend = _trend_score(bars)
    volume = _volume_score(bars)

    total = round(mom * 0.30 + vol * 0.25 + trend * 0.25 + volume * 0.20)
    total = max(0, min(100, total))

    return ScoreCard(
        total=total,
        momentum=mom,
        volatility=vol,
        trend=trend,
        volume=volume,
    )
