#!/usr/bin/env python3
"""session_quality.py — Detect dead-session conditions (VWAP-flat / Asia chop).

Inspiration from "How to Connect Claude to TradingView" YouTube video where
the host says: "Asia some nights completely flat. I lost two trades. I know
better than to trade that."

Wally already has `macro_gate.py` for macro events. This module adds a
session-quality gate that detects micro-structural dead zones independent of
macro calendar — useful for crypto/forex during low-volume hours where the
chart "looks like a flat line."

Logic:
  - Pull last 12-20 bars (15m default) from Binance public API
  - Compute VWAP standard deviation as % of mean price
  - If std_pct < FLAT_THRESHOLD (default 0.10%) → BLOCK
  - Also flag if last 8 bars range < 0.5% (no real movement)

Used by: trade-validator + signal-validator agents (gate before 4 filters).

Exit codes:
  0 = OK to trade (session active)
  1 = BLOCK (session dead — flat VWAP or compressed range)
  2 = WARN (low quality but tradeable; reduce size)

Output: JSON to stdout, human-readable to stderr.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone
from typing import Any

# Thresholds
DEFAULT_FLAT_THRESHOLD_PCT = 0.10  # std/mean < 0.10% = flat
DEFAULT_RANGE_THRESHOLD_PCT = 0.50  # last-8-bars range < 0.50% = compressed
DEFAULT_BARS = 12
DEFAULT_TF = "15m"


def fetch_klines(symbol: str, interval: str = "15m", limit: int = 12) -> list[list[Any]]:
    """Fetch OHLCV from Binance public API. No API key required."""
    url = (
        f"https://api.binance.com/api/v3/klines"
        f"?symbol={symbol.upper()}&interval={interval}&limit={limit}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "wally-trader/1.0"})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read())


def compute_vwap_dispersion(bars: list[list[Any]]) -> dict[str, float]:
    """Compute VWAP and dispersion of typical-price around VWAP."""
    typical_vol_sum = 0.0
    vol_sum = 0.0
    typicals = []
    for b in bars:
        h, lo, c, vol = float(b[2]), float(b[3]), float(b[4]), float(b[5])
        typical = (h + lo + c) / 3.0
        typical_vol_sum += typical * vol
        vol_sum += vol
        typicals.append(typical)

    if vol_sum == 0 or not typicals:
        return {"vwap": 0.0, "std_pct": 0.0, "mean": 0.0}

    vwap = typical_vol_sum / vol_sum
    mean = sum(typicals) / len(typicals)
    var = sum((t - vwap) ** 2 for t in typicals) / len(typicals)
    std = var ** 0.5
    std_pct = (std / mean) * 100.0 if mean else 0.0
    return {"vwap": vwap, "std_pct": std_pct, "mean": mean}


def compute_range_pct(bars: list[list[Any]], n: int = 8) -> float:
    """Range of last N bars as % of last close."""
    recent = bars[-n:]
    highs = [float(b[2]) for b in recent]
    lows = [float(b[3]) for b in recent]
    last_close = float(bars[-1][4])
    if last_close == 0:
        return 0.0
    return (max(highs) - min(lows)) / last_close * 100.0


def assess_session(
    symbol: str,
    interval: str = DEFAULT_TF,
    bars: int = DEFAULT_BARS,
    flat_threshold: float = DEFAULT_FLAT_THRESHOLD_PCT,
    range_threshold: float = DEFAULT_RANGE_THRESHOLD_PCT,
) -> dict[str, Any]:
    """Return session-quality assessment with verdict + reasoning."""
    try:
        klines = fetch_klines(symbol, interval, bars)
    except Exception as e:
        return {
            "verdict": "ERROR",
            "reason": f"failed to fetch klines: {e}",
            "symbol": symbol,
        }

    if len(klines) < bars:
        return {
            "verdict": "ERROR",
            "reason": f"insufficient bars: got {len(klines)} need {bars}",
            "symbol": symbol,
        }

    vwap_data = compute_vwap_dispersion(klines)
    range_pct = compute_range_pct(klines, n=min(8, bars))

    flat_flag = vwap_data["std_pct"] < flat_threshold
    compressed_flag = range_pct < range_threshold

    if flat_flag and compressed_flag:
        verdict = "BLOCK"
        reason = (
            f"Dead session: VWAP std {vwap_data['std_pct']:.3f}% < {flat_threshold:.2f}% "
            f"AND {min(8, bars)}-bar range {range_pct:.2f}% < {range_threshold:.2f}%. "
            f"Chart is flat — high probability of false signals + chop SL."
        )
    elif flat_flag or compressed_flag:
        verdict = "WARN"
        which = "VWAP-flat" if flat_flag else "range-compressed"
        reason = (
            f"Low-quality session: {which}. VWAP std {vwap_data['std_pct']:.3f}%, "
            f"range {range_pct:.2f}%. Reduce size 50% or wait for breakout."
        )
    else:
        verdict = "OK"
        reason = (
            f"Session active: VWAP std {vwap_data['std_pct']:.3f}%, "
            f"range {range_pct:.2f}%. Tradeable."
        )

    return {
        "verdict": verdict,
        "reason": reason,
        "symbol": symbol,
        "interval": interval,
        "bars": bars,
        "vwap": round(vwap_data["vwap"], 6),
        "vwap_std_pct": round(vwap_data["std_pct"], 4),
        "range_pct_8bars": round(range_pct, 3),
        "thresholds": {
            "flat_pct": flat_threshold,
            "range_pct": range_threshold,
        },
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Session-quality gate (VWAP-flat detector)")
    p.add_argument("--symbol", default="BTCUSDT", help="Asset symbol on Binance (default BTCUSDT)")
    p.add_argument("--interval", default=DEFAULT_TF, help="Timeframe (default 15m)")
    p.add_argument("--bars", type=int, default=DEFAULT_BARS, help="Number of bars (default 12)")
    p.add_argument(
        "--flat-threshold",
        type=float,
        default=DEFAULT_FLAT_THRESHOLD_PCT,
        help="VWAP std%% threshold for flat detection (default 0.10)",
    )
    p.add_argument(
        "--range-threshold",
        type=float,
        default=DEFAULT_RANGE_THRESHOLD_PCT,
        help="8-bar range%% threshold for compression (default 0.50)",
    )
    p.add_argument("--quick", action="store_true", help="One-line stderr summary")
    args = p.parse_args()

    result = assess_session(
        symbol=args.symbol,
        interval=args.interval,
        bars=args.bars,
        flat_threshold=args.flat_threshold,
        range_threshold=args.range_threshold,
    )

    if args.quick:
        print(
            f"[session-quality] {result['symbol']} {result['interval']}: "
            f"{result['verdict']} | {result['reason']}",
            file=sys.stderr,
        )

    print(json.dumps(result, indent=2))

    if result["verdict"] == "BLOCK":
        return 1
    if result["verdict"] == "WARN":
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
