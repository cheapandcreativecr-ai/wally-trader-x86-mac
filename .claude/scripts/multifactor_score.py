#!/usr/bin/env python3
"""
multifactor_score.py — Multi-Factor scoring 0-100 adaptado a cripto/forex.
Imports wally_core.multifactor for the composite_score API; keeps local
sub-scorers because they compute a richer breakdown (RSI/ADX/EMA details,
ATR percentile, volume spike) not exposed by wally_core.multifactor.

Factores (cripto-friendly, sin fundamentals):
  1. Momentum   (0-25): RSI(14) + ADX(14) direccional + EMA20 vs EMA50
  2. Volatility (0-25): ATR(14) percentile vs últimos 90 bars (sweet spot 30-70%)
  3. Trend Quality (0-25): EMA alignment (EMA20>EMA50>EMA200 = bull full)
  4. Volume (0-25): spike ratio del último bar vs avg 20

Score total: 0-100 (LONG bias positivo, SHORT bias negativo).

Filosofía: meta-score complementario al ML XGBoost. Si ambos coinciden
(ML>60 + multifactor>60) → conviction alta. Si divergen → flag de cautela.

Usage:
    python3 multifactor_score.py --bars-file /tmp/bars1h.json
    python3 multifactor_score.py --bars-file /tmp/bars1h.json --json
    python3 multifactor_score.py --bars-file /tmp/bars1h.json --side long
"""
import argparse
import json
import math
import sys
from pathlib import Path

# Auto-inject wally_core from worktree (no venv activation required)
_SHARED = Path(__file__).resolve().parent.parent.parent / "shared/wally_core/src"
if _SHARED.exists() and str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from wally_core.multifactor import composite_score as _wc_composite_score  # noqa: E402, F401


def parse_bars(path):
    data = json.loads(Path(path).read_text())
    if isinstance(data, dict) and "bars" in data:
        data = data["bars"]
    elif isinstance(data, dict) and "ohlcv" in data:
        data = data["ohlcv"]
    out = []
    for bar in data:
        if isinstance(bar, dict):
            out.append({
                "open": float(bar.get("open") or bar.get("o")),
                "high": float(bar.get("high") or bar.get("h")),
                "low": float(bar.get("low") or bar.get("l")),
                "close": float(bar.get("close") or bar.get("c")),
                "volume": float(bar.get("volume") or bar.get("v") or 0),
            })
        elif isinstance(bar, (list, tuple)) and len(bar) >= 5:
            out.append({
                "open": float(bar[1]), "high": float(bar[2]),
                "low": float(bar[3]), "close": float(bar[4]),
                "volume": float(bar[5]) if len(bar) > 5 else 0,
            })
    return out


def ema(values, period):
    if not values:
        return []
    k = 2 / (period + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def atr(bars, period=14):
    if len(bars) < period + 1:
        return 0.0
    trs = []
    for i in range(1, len(bars)):
        h, l, pc = bars[i]["high"], bars[i]["low"], bars[i-1]["close"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(trs[-period:]) / period


def adx_simple(bars, period=14):
    """Simplified ADX: mean of |close_change| / atr ratio over period."""
    if len(bars) < period + 1:
        return 0.0
    closes = [b["close"] for b in bars]
    moves = [abs(closes[i] - closes[i-1]) for i in range(1, len(closes))]
    avg_move = sum(moves[-period:]) / period
    a = atr(bars, period)
    if a == 0:
        return 0.0
    # Crude proxy: ADX-like in [0, 100]. Real ADX is more involved.
    return min(100, (avg_move / a) * 50)


def percentile(value, sample):
    if not sample:
        return 50.0
    sorted_s = sorted(sample)
    below = sum(1 for x in sorted_s if x < value)
    return (below / len(sorted_s)) * 100


def score_momentum(bars):
    """RSI + ADX + EMA20/50 slope. Returns dict with score (-25..+25) and details."""
    closes = [b["close"] for b in bars]
    r = rsi(closes, 14)
    adx_val = adx_simple(bars, 14)
    ema20 = ema(closes, 20)[-1]
    ema50 = ema(closes, 50)[-1] if len(closes) >= 50 else ema20

    # RSI: <30 oversold (long bias), 30-50 weak, 50-70 strong, >70 overbought (short bias)
    if r < 30:
        rsi_pts = +8  # contrarian long
    elif r < 50:
        rsi_pts = -3  # weak
    elif r < 70:
        rsi_pts = +5  # strong long
    else:
        rsi_pts = -8  # overbought short bias

    # ADX strength (ignores direction, multiplier on momentum)
    if adx_val > 25:
        strength = 1.5
    elif adx_val > 20:
        strength = 1.0
    else:
        strength = 0.5

    # EMA20 vs EMA50: alignment
    ema_diff_pct = (ema20 - ema50) / ema50 * 100 if ema50 else 0
    if ema_diff_pct > 0.5:
        ema_pts = +6
    elif ema_diff_pct > 0:
        ema_pts = +2
    elif ema_diff_pct > -0.5:
        ema_pts = -2
    else:
        ema_pts = -6

    raw = rsi_pts + ema_pts
    scaled = max(-25, min(25, raw * strength))

    return {
        "score": round(scaled, 2),
        "rsi": round(r, 2),
        "adx": round(adx_val, 2),
        "ema20_vs_ema50_pct": round(ema_diff_pct, 3),
        "strength_mult": strength,
    }


def score_volatility(bars, lookback=90):
    """ATR percentile vs últimos `lookback` bars. Sweet spot: 30-70%-ile = +25."""
    if len(bars) < lookback + 14:
        return {"score": 0, "atr_pct": None, "note": "insufficient_data"}

    # Compute rolling ATR over the last `lookback` bars
    historical_atrs = []
    for i in range(14, lookback):
        window = bars[-(lookback - i + 14):-(lookback - i)]
        if len(window) >= 14:
            historical_atrs.append(atr(window, 14))

    current_atr = atr(bars[-15:], 14)
    if not historical_atrs:
        return {"score": 0, "atr_pct": None}
    pct = percentile(current_atr, historical_atrs)

    # Score: sweet spot 30-70%-ile = max +25 (good vol for trading).
    # Edges (<10 or >90) = lowest = 0 (too quiet or too explosive)
    if 30 <= pct <= 70:
        sc = 25
    elif 20 <= pct <= 80:
        sc = 18
    elif 10 <= pct <= 90:
        sc = 10
    else:
        sc = 3
    return {"score": sc, "atr_pct": round(pct, 1), "current_atr": round(current_atr, 4)}


def score_trend_quality(bars):
    """EMA alignment 20>50>200 (bull full = +25, bear full = -25, mixed = 0±10)."""
    closes = [b["close"] for b in bars]
    if len(closes) < 200:
        # Soften requirement: use 50 as max
        e20 = ema(closes, 20)[-1]
        e50 = ema(closes, 50)[-1] if len(closes) >= 50 else e20
        if e20 > e50 * 1.005:
            return {"score": 12, "alignment": "PARTIAL_BULL", "ema20": e20, "ema50": e50}
        elif e20 < e50 * 0.995:
            return {"score": -12, "alignment": "PARTIAL_BEAR", "ema20": e20, "ema50": e50}
        return {"score": 0, "alignment": "FLAT", "ema20": e20, "ema50": e50}

    e20 = ema(closes, 20)[-1]
    e50 = ema(closes, 50)[-1]
    e200 = ema(closes, 200)[-1]
    cur = closes[-1]

    if cur > e20 > e50 > e200:
        return {"score": 25, "alignment": "FULL_BULL", "ema20": e20, "ema50": e50, "ema200": e200}
    if cur < e20 < e50 < e200:
        return {"score": -25, "alignment": "FULL_BEAR", "ema20": e20, "ema50": e50, "ema200": e200}
    if e20 > e50 > e200:
        return {"score": 15, "alignment": "BULL_PULLBACK", "ema20": e20, "ema50": e50, "ema200": e200}
    if e20 < e50 < e200:
        return {"score": -15, "alignment": "BEAR_BOUNCE", "ema20": e20, "ema50": e50, "ema200": e200}
    return {"score": 0, "alignment": "MIXED", "ema20": e20, "ema50": e50, "ema200": e200}


def score_volume(bars):
    """Last bar volume vs avg of last 20. Spike >2x = +25; <1x = 0."""
    if len(bars) < 21:
        return {"score": 0, "spike_ratio": None}
    last = bars[-1]["volume"]
    avg = sum(b["volume"] for b in bars[-21:-1]) / 20
    if avg <= 0:
        return {"score": 0, "spike_ratio": None}
    ratio = last / avg
    if ratio >= 2.5:
        sc = 25
    elif ratio >= 2.0:
        sc = 22
    elif ratio >= 1.5:
        sc = 17
    elif ratio >= 1.0:
        sc = 10
    else:
        sc = 3
    return {"score": sc, "spike_ratio": round(ratio, 2)}


def main():
    p = argparse.ArgumentParser(description="Multi-Factor scoring 0-100")
    p.add_argument("--bars-file", required=True)
    p.add_argument("--side", choices=["long", "short"], help="Filtrar score por side")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    bars = parse_bars(args.bars_file)
    if len(bars) < 50:
        raise SystemExit(f"ERROR: necesitas 50+ bars, recibí {len(bars)}")

    momentum = score_momentum(bars)
    vol = score_volatility(bars)
    trend = score_trend_quality(bars)
    volume = score_volume(bars)

    # Total score: -100 a +100 (negativo = bear bias)
    total = momentum["score"] + trend["score"] + (
        # Vol y volume son no-direccionales, suman al lado del trend
        vol["score"] + volume["score"]
    ) * (1 if (momentum["score"] + trend["score"]) >= 0 else -1)
    total = max(-100, min(100, total))

    # Side-specific
    if args.side == "long":
        side_score = max(0, total)
    elif args.side == "short":
        side_score = max(0, -total)
    else:
        side_score = abs(total)

    # Conviction label
    abs_t = abs(total)
    if abs_t >= 70:
        conv = "ALTA"
    elif abs_t >= 50:
        conv = "MEDIA"
    elif abs_t >= 30:
        conv = "BAJA"
    else:
        conv = "FLAT"

    direction = "LONG" if total > 5 else ("SHORT" if total < -5 else "NEUTRAL")

    result = {
        "total_score": round(total, 2),
        "abs_score": round(abs_t, 2),
        "direction": direction,
        "conviction": conv,
        "side_score": round(side_score, 2) if args.side else None,
        "factors": {
            "momentum": momentum,
            "volatility": vol,
            "trend_quality": trend,
            "volume": volume,
        }
    }

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print(f"╔══════════════════════════════════════════════════════════════════╗")
    print(f"║  Multi-Factor Score                                              ║")
    print(f"╚══════════════════════════════════════════════════════════════════╝")
    print(f"")
    print(f"TOTAL: {total:+.1f} / 100  →  {direction} | {conv}")
    if args.side:
        print(f"Side score ({args.side.upper()}): {side_score:.1f} / 100")
    print(f"")
    print(f"Breakdown:")
    print(f"  Momentum         : {momentum['score']:+.2f}  "
          f"(RSI={momentum['rsi']}, ADX={momentum['adx']}, "
          f"EMA20-50={momentum['ema20_vs_ema50_pct']:+.2f}%)")
    print(f"  Trend Quality    : {trend['score']:+.2f}  ({trend['alignment']})")
    print(f"  Volatility       : {vol['score']:+.2f}  "
          f"(ATR percentile={vol.get('atr_pct')}%)")
    print(f"  Volume           : {volume['score']:+.2f}  "
          f"(spike={volume.get('spike_ratio')}x)")
    print(f"")
    print(f"Reglas de uso:")
    print(f"  - Score > 70 + ML > 60  → conviction MAX, full size")
    print(f"  - Score 50-70 + ML > 60 → conviction medium, size 75%")
    print(f"  - Score y ML divergen   → flag, reducir size 50% o skip")
    print(f"  - Score < 30            → setup débil, esperar mejor")


if __name__ == "__main__":
    main()
