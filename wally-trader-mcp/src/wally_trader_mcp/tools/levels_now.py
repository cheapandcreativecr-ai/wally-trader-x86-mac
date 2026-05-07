"""levels_now tool — return current Donchian/BB/RSI/ATR for given bars."""
import json
import statistics
from pathlib import Path


def levels_now(
    bars_path: str,
    donchian_length: int = 15,
    bb_length: int = 20,
    rsi_length: int = 14,
    atr_length: int = 14,
) -> dict:
    """Compute current technical levels from OHLCV bars.

    Args:
        bars_path: path to JSON file with list of {open, high, low, close, volume} dicts
        donchian_length: number of bars for Donchian channel (default 15)
        bb_length: number of bars for Bollinger Bands (default 20)
        rsi_length: RSI period — Wilder smoothing (default 14)
        atr_length: ATR period — Wilder smoothing (default 14)

    Returns:
        dict with last_close, donchian {high, low}, bollinger {mid, upper, lower},
        rsi, atr — or {'error': ...} if bars are insufficient.
    """
    bars = json.loads(Path(bars_path).read_text())
    min_required = max(donchian_length, bb_length, rsi_length + 1, atr_length + 1)
    if len(bars) < min_required:
        return {"error": f"insufficient bars: need {min_required}, got {len(bars)}"}

    closes = [float(b["close"]) for b in bars]
    highs = [float(b["high"]) for b in bars]
    lows = [float(b["low"]) for b in bars]

    # ── Donchian Channel ────────────────────────────────────────────────────────
    donch_window = bars[-donchian_length:]
    donchian = {
        "high": max(float(b["high"]) for b in donch_window),
        "low": min(float(b["low"]) for b in donch_window),
    }

    # ── Bollinger Bands (20, 2σ) ────────────────────────────────────────────────
    bb_window = closes[-bb_length:]
    bb_mean = statistics.fmean(bb_window)
    bb_std = statistics.pstdev(bb_window)
    bollinger = {
        "mid": round(bb_mean, 4),
        "upper": round(bb_mean + 2 * bb_std, 4),
        "lower": round(bb_mean - 2 * bb_std, 4),
    }

    # ── RSI (Wilder smoothing) ──────────────────────────────────────────────────
    gains, losses = [], []
    for i in range(1, rsi_length + 1):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    avg_g = sum(gains) / rsi_length
    avg_l = sum(losses) / rsi_length
    for i in range(rsi_length + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        avg_g = (avg_g * (rsi_length - 1) + max(d, 0.0)) / rsi_length
        avg_l = (avg_l * (rsi_length - 1) + max(-d, 0.0)) / rsi_length
    rs = avg_g / avg_l if avg_l else float("inf")
    rsi = 100.0 - 100.0 / (1.0 + rs)

    # ── ATR (Wilder smoothing) ──────────────────────────────────────────────────
    trs = []
    for i in range(1, atr_length + 1):
        h, l, prev_c = highs[i], lows[i], closes[i - 1]
        trs.append(max(h - l, abs(h - prev_c), abs(l - prev_c)))
    atr = sum(trs) / atr_length
    for i in range(atr_length + 1, len(closes)):
        h, l, prev_c = highs[i], lows[i], closes[i - 1]
        tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
        atr = (atr * (atr_length - 1) + tr) / atr_length

    return {
        "last_close": closes[-1],
        "donchian": donchian,
        "bollinger": bollinger,
        "rsi": round(rsi, 2),
        "atr": round(atr, 4),
    }
