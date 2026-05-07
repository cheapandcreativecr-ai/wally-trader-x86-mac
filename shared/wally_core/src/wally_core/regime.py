"""ADX-based regime detection."""
from __future__ import annotations
from enum import Enum


class RegimeLabel(str, Enum):
    RANGE_CHOP = "RANGE_CHOP"
    TREND_LEVE = "TREND_LEVE"
    TREND_FUERTE = "TREND_FUERTE"
    TREND_EXTREMO = "TREND_EXTREMO"
    VOLATILE = "VOLATILE"


def compute_adx(bars: list[dict], length: int = 14) -> dict:
    """Compute ADX, +DI, -DI from OHLCV bars.

    Bars: list of {open, high, low, close, volume}.
    Returns dict with keys: adx, plus_di, minus_di.
    """
    if len(bars) < length * 2:
        raise ValueError(f"Need at least {length * 2} bars, got {len(bars)}")

    highs = [float(b["high"]) for b in bars]
    lows = [float(b["low"]) for b in bars]
    closes = [float(b["close"]) for b in bars]

    plus_dm = []
    minus_dm = []
    tr = []
    for i in range(1, len(bars)):
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]
        plus_dm.append(up_move if (up_move > down_move and up_move > 0) else 0.0)
        minus_dm.append(down_move if (down_move > up_move and down_move > 0) else 0.0)
        tr.append(max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        ))

    def smooth(arr: list[float], n: int) -> list[float]:
        out = [sum(arr[:n])]
        for v in arr[n:]:
            out.append(out[-1] - out[-1] / n + v)
        return out

    sm_plus = smooth(plus_dm, length)
    sm_minus = smooth(minus_dm, length)
    sm_tr = smooth(tr, length)

    plus_di = [100 * p / t if t else 0 for p, t in zip(sm_plus, sm_tr)]
    minus_di = [100 * m / t if t else 0 for m, t in zip(sm_minus, sm_tr)]

    dx = [
        100 * abs(p - m) / (p + m) if (p + m) else 0
        for p, m in zip(plus_di, minus_di)
    ]
    if len(dx) < length:
        raise ValueError("Insufficient bars to compute ADX")
    adx_smoothed = sum(dx[:length]) / length
    for v in dx[length:]:
        adx_smoothed = (adx_smoothed * (length - 1) + v) / length

    return {
        "adx": round(adx_smoothed, 2),
        "plus_di": round(plus_di[-1], 2),
        "minus_di": round(minus_di[-1], 2),
    }


def label_regime(adx: float, plus_di: float, minus_di: float) -> RegimeLabel:
    """Map ADX numeric to regime label per CLAUDE.md thresholds."""
    if adx < 20:
        return RegimeLabel.RANGE_CHOP
    if adx < 25:
        return RegimeLabel.RANGE_CHOP
    if adx < 30:
        return RegimeLabel.TREND_LEVE
    if adx < 40:
        return RegimeLabel.TREND_FUERTE
    return RegimeLabel.TREND_EXTREMO
