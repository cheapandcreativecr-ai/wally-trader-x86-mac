"""4-filter Mean Reversion setup validation."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import statistics


class Side(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class FilterResult:
    name: str
    passed: bool
    detail: str


@dataclass
class ValidateResult:
    go: bool
    filters: list[FilterResult]
    reason: str


def _rsi(closes: list[float], length: int = 14) -> float:
    if len(closes) < length + 1:
        raise ValueError("not enough closes for RSI")
    gains = []
    losses = []
    for i in range(1, length + 1):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains) / length
    avg_loss = sum(losses) / length
    for i in range(length + 1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gain = max(diff, 0)
        loss = max(-diff, 0)
        avg_gain = (avg_gain * (length - 1) + gain) / length
        avg_loss = (avg_loss * (length - 1) + loss) / length
    rs = avg_gain / avg_loss if avg_loss else float("inf")
    return 100 - 100 / (1 + rs)


def _bollinger(closes: list[float], length: int = 20, std_mult: float = 2.0):
    if len(closes) < length:
        raise ValueError("not enough closes for BB")
    window = closes[-length:]
    mean = statistics.fmean(window)
    sd = statistics.pstdev(window)
    return {"upper": mean + std_mult * sd, "lower": mean - std_mult * sd, "mid": mean}


def _donchian(bars: list[dict], length: int = 15):
    window = bars[-length:]
    return {"high": max(b["high"] for b in window), "low": min(b["low"] for b in window)}


def validate_setup(bars: list[dict], side: Side, donchian_length: int = 15) -> ValidateResult:
    """Apply 4-filter Mean Reversion check on the latest bar.

    LONG passes when: donchian-low touched (±0.1%), RSI<35, low touches BB-lower, close green.
    SHORT mirrors.
    """
    if len(bars) < max(donchian_length, 20) + 1:
        raise ValueError("not enough bars")

    last = bars[-1]
    closes = [float(b["close"]) for b in bars]
    last_close = float(last["close"])
    last_open = float(last["open"])
    last_high = float(last["high"])
    last_low = float(last["low"])

    rsi = _rsi(closes)
    bb = _bollinger(closes)
    donch = _donchian(bars, donchian_length)

    filters: list[FilterResult] = []
    if side == Side.LONG:
        donch_pct = abs(last_low - donch["low"]) / donch["low"]
        filters.append(FilterResult(
            "donchian_extreme",
            donch_pct <= 0.001,
            f"low={last_low} donch_low={donch['low']} pct={donch_pct:.4f}"
        ))
        filters.append(FilterResult("rsi_oversold", rsi < 35, f"rsi={rsi:.2f}"))
        filters.append(FilterResult("bb_touch", last_low <= bb["lower"], f"low={last_low} bb_lower={bb['lower']:.2f}"))
        filters.append(FilterResult("candle_color", last_close > last_open, f"close={last_close} open={last_open}"))
    else:  # SHORT
        donch_pct = abs(last_high - donch["high"]) / donch["high"]
        filters.append(FilterResult(
            "donchian_extreme",
            donch_pct <= 0.001,
            f"high={last_high} donch_high={donch['high']} pct={donch_pct:.4f}"
        ))
        filters.append(FilterResult("rsi_oversold", rsi > 65, f"rsi={rsi:.2f}"))
        filters.append(FilterResult("bb_touch", last_high >= bb["upper"], f"high={last_high} bb_upper={bb['upper']:.2f}"))
        filters.append(FilterResult("candle_color", last_close < last_open, f"close={last_close} open={last_open}"))

    go = all(f.passed for f in filters)
    failed = [f.name for f in filters if not f.passed]
    reason = "all 4 filters passed" if go else f"failed: {', '.join(failed)}"
    return ValidateResult(go=go, filters=filters, reason=reason)
