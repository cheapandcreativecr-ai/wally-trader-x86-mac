#!/usr/bin/env python3
"""Setup TradingView alerts via MCP for a position's SL+TPs.

Usage:
    python3 setup_tv_alerts.py --symbol BINANCE:LDOUSDT.P \
        --entry 0.3982 --sl 0.4180 \
        --tps 0.3961:25,0.3925:25,0.3982:25,0.3862:25
"""
from __future__ import annotations
import argparse
import json
import sys


def setup_alerts(*, symbol: str, entry: float, sl: float, tps: list[tuple[float, int]]):
    """Create TV alerts via MCP. Returns list of created alert IDs."""
    alerts = []

    # SL alert
    alerts.append({
        "label": f"SL {symbol} @ {sl}",
        "price": sl,
        "condition": "crossing",
        "message_when_fires": f"SL HIT {symbol} @ {sl} — close position immediately",
    })

    # TP alerts
    for tp_price, pct_close in tps:
        alerts.append({
            "label": f"TP {pct_close}% {symbol} @ {tp_price}",
            "price": tp_price,
            "condition": "crossing",
            "message_when_fires": f"TP {pct_close}% {symbol} @ {tp_price} — close {pct_close}% of position",
        })

    # Print the TV MCP commands the user can run via Claude Code OR via a future automation:
    print(f"=== Alerts to create for {symbol} ===")
    print(f"Entry: ${entry}")
    print(f"SL: ${sl}")
    for tp_price, pct in tps:
        print(f"TP {pct}%: ${tp_price}")
    print()
    print("Use these MCP calls (or via Claude Code with tradingview MCP):")
    for a in alerts:
        print(f"  mcp__tradingview__alert_create("
              f"symbol={symbol!r}, "
              f"price={a['price']}, "
              f"condition={a['condition']!r}, "
              f"label={a['label']!r})")

    # Output JSON for programmatic use
    return {
        "symbol": symbol,
        "entry": entry,
        "sl": sl,
        "alerts_to_create": alerts,
    }


def _cli():
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", required=True, help="e.g. BINANCE:LDOUSDT.P or Bitunix:LDOUSDT.P")
    p.add_argument("--entry", type=float, required=True)
    p.add_argument("--sl", type=float, required=True)
    p.add_argument("--tps", required=True, help="comma-sep price:pct, e.g. 0.39:25,0.385:50")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    tps = []
    for tp_str in args.tps.split(","):
        price_s, pct_s = tp_str.split(":")
        tps.append((float(price_s), int(pct_s)))

    result = setup_alerts(symbol=args.symbol, entry=args.entry, sl=args.sl, tps=tps)

    if args.json:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    _cli()
