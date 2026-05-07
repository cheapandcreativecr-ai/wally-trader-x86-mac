"""macross_signal tool — EMA(9/21) cross detector for trending regime."""
import json
from pathlib import Path


def _ema(values: list[float], length: int) -> list[float]:
    """Compute exponential moving average using standard multiplier 2/(length+1)."""
    if not values:
        return []
    k = 2.0 / (length + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(out[-1] + k * (v - out[-1]))
    return out


def macross_signal(
    bars_path: str,
    fast: int = 9,
    slow: int = 21,
) -> dict:
    """Detect EMA(fast)/EMA(slow) crossover signal in the latest bars.

    Looks back up to 5 bars from the end to detect a fresh cross.

    Args:
        bars_path: path to JSON file with list of {open, high, low, close, volume} dicts
        fast: fast EMA period (default 9)
        slow: slow EMA period (default 21)

    Returns:
        dict with:
            signal: 'LONG' | 'SHORT' | 'NONE'
            ema_fast: last fast EMA value
            ema_slow: last slow EMA value
            last_close: last close price
            cross_at_index: bar index where cross occurred, or None
    """
    bars = json.loads(Path(bars_path).read_text())
    closes = [float(b["close"]) for b in bars]

    if len(closes) < slow + 2:
        return {
            "signal": "NONE",
            "reason": f"insufficient bars: need {slow + 2}, got {len(closes)}",
            "ema_fast": None,
            "ema_slow": None,
            "last_close": closes[-1] if closes else None,
            "cross_at_index": None,
        }

    ef = _ema(closes, fast)
    es = _ema(closes, slow)

    cross_idx = None
    direction = "NONE"

    # Scan last 5 bars for a fresh cross (most recent wins)
    scan_start = max(slow, len(closes) - 5)
    for i in range(scan_start, len(closes)):
        if i < 1:
            continue
        if ef[i - 1] <= es[i - 1] and ef[i] > es[i]:
            cross_idx = i
            direction = "LONG"
            break
        if ef[i - 1] >= es[i - 1] and ef[i] < es[i]:
            cross_idx = i
            direction = "SHORT"
            break

    return {
        "signal": direction,
        "ema_fast": round(ef[-1], 4),
        "ema_slow": round(es[-1], 4),
        "last_close": closes[-1],
        "cross_at_index": cross_idx,
    }
