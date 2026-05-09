#!/usr/bin/env python3
"""Auto SL/TP placement helper. CLI: --entry --side --atr-pct --regime."""
import sys
import argparse
import json
from pathlib import Path

_SHARED = Path(__file__).resolve().parent.parent.parent / "shared/wally_core/src"
if _SHARED.exists() and str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from wally_core.atr_sl import volatility_adjusted_sl, auto_tp_levels


def main():
    p = argparse.ArgumentParser(description="Compute volatility-adjusted SL + 4 TPs")
    p.add_argument("--entry", type=float, required=True, help="Entry price")
    p.add_argument("--side", choices=["LONG", "SHORT"], required=True)
    p.add_argument("--atr-pct", type=float, required=True, help="ATR as percentage of price")
    p.add_argument("--regime", default="RANGE_CHOP",
                   choices=["RANGE_CHOP", "TREND_LEVE", "TREND_FUERTE", "TREND_EXTREMO", "VOLATILE"],
                   help="Market regime from /regime")
    p.add_argument("--json", action="store_true", help="Output raw JSON")
    args = p.parse_args()

    sl_data = volatility_adjusted_sl(args.entry, args.side, args.atr_pct, args.regime)
    tps = auto_tp_levels(args.entry, sl_data["sl_price"], args.side)

    output = {
        "entry": args.entry,
        "side": args.side,
        "regime": args.regime,
        "sl": sl_data,
        "tps": tps,
    }

    if args.json:
        print(json.dumps(output, indent=2))
    else:
        print(f"=== Auto SL/TP for {args.side} @ ${args.entry:,.2f} ===")
        print(f"Regime: {args.regime}  |  ATR: {args.atr_pct}%  |  Mult: {sl_data['multiplier_used']}")
        print(f"SL:  ${sl_data['sl_price']:,.2f}  ({sl_data['sl_distance_pct']:.3f}% from entry)")
        print(f"TP1 (25%): ${tps['tp1']:,.2f}  R:R 2.5")
        print(f"TP2 (25%): ${tps['tp2']:,.2f}  R:R 4.0")
        print(f"TP3 (25%): ${tps['tp3']:,.2f}  R:R 6.0")
        print(f"TP4 (25%): ${tps['tp4']:,.2f}  R:R 8.0")


if __name__ == "__main__":
    main()
