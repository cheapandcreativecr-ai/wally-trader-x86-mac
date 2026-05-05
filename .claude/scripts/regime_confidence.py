#!/usr/bin/env python3
"""regime_confidence — position sizing by regime backtest expectancy.

Formula: size_mult = clip(pnl_per_trade / 2.0, min=0.3, max=1.5)
"""

from __future__ import annotations

import argparse
import json

MIN_MULT = 0.30
MAX_MULT = 1.50
DIVISOR = 2.0
LEVERAGE = 10


def compute(pnl_per_trade: float, base_margin: float = 4.0,
            dynamic: bool = True) -> dict:
    if not dynamic:
        size_mult = 1.0
    else:
        raw = pnl_per_trade / DIVISOR
        size_mult = max(MIN_MULT, min(MAX_MULT, raw))
    margin = round(base_margin * size_mult, 2)
    return {
        "pnl_per_trade": pnl_per_trade,
        "size_mult": round(size_mult, 2),
        "margin_usd": margin,
        "notional_10x": round(margin * LEVERAGE, 2),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--pnl-per-trade", type=float, required=True)
    p.add_argument("--base-margin", type=float, default=4.0)
    p.add_argument("--no-dynamic", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    out = compute(args.pnl_per_trade, args.base_margin,
                  dynamic=not args.no_dynamic)
    if args.json:
        print(json.dumps(out))
    else:
        print(f"size_mult={out['size_mult']}  margin=${out['margin_usd']}  "
              f"notional={out['notional_10x']}")


if __name__ == "__main__":
    main()
