#!/usr/bin/env python3
"""ASCII sparkline chart for OHLCV data using Unicode block characters."""
import sys
import argparse
import json
import urllib.request


BLOCKS = " ▁▂▃▄▅▆▇█"


def render_sparkline(values: list, width: int = 60) -> str:
    """Render values as Unicode block sparkline."""
    if not values:
        return ""

    # Resample to fit width
    if len(values) > width:
        step = len(values) / width
        sampled = [values[int(i * step)] for i in range(width)]
    else:
        sampled = values

    lo = min(sampled)
    hi = max(sampled)
    rng = hi - lo if hi > lo else 1

    chars = []
    for v in sampled:
        idx = int((v - lo) / rng * (len(BLOCKS) - 1))
        chars.append(BLOCKS[idx])

    return "".join(chars)


def fetch_klines(symbol: str, interval: str = "1h", limit: int = 60) -> list:
    """Fetch from Binance."""
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        return [{"close": float(b[4]), "high": float(b[2]), "low": float(b[3])} for b in data]
    except Exception as e:
        print(f"Failed to fetch {symbol}: {e}", file=sys.stderr)
        return []


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="BTCUSDT")
    p.add_argument("--tf", default="1h")
    p.add_argument("--bars", type=int, default=60)
    p.add_argument("--width", type=int, default=60)
    args = p.parse_args()

    bars = fetch_klines(args.symbol, args.tf, args.bars)
    if not bars:
        sys.exit(1)

    closes = [b["close"] for b in bars]
    spark = render_sparkline(closes, args.width)

    lo = min(closes)
    hi = max(closes)
    cur = closes[-1]
    pct = (cur - closes[0]) / closes[0] * 100 if closes[0] else 0

    print(f"{args.symbol} ({args.tf}) -- last {len(bars)} bars")
    print(f"   {spark}")
    print(f"   Range: ${lo:.6g} - ${hi:.6g}  |  Now: ${cur:.6g}  ({pct:+.2f}%)")


if __name__ == "__main__":
    main()
