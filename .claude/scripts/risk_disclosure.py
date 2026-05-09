#!/usr/bin/env python3
"""Risk disclosure prompt for trades >15% capital."""
import sys
import argparse


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--margin", type=float, required=True)
    p.add_argument("--capital", type=float, required=True)
    p.add_argument("--leverage", type=int, required=True)
    p.add_argument("--threshold-pct", type=float, default=15.0)
    p.add_argument("--no-input", action="store_true", help="Print disclosure but do not prompt")
    args = p.parse_args()

    pct = args.margin / args.capital * 100
    notional = args.margin * args.leverage

    if pct < args.threshold_pct:
        print(f"✓ Margin {pct:.1f}% capital — below threshold {args.threshold_pct}%")
        sys.exit(0)

    print("=" * 60)
    print(f"⚠️  HIGH-RISK TRADE — disclosure required")
    print("=" * 60)
    print(f"Margin:    ${args.margin:.2f}  ({pct:.1f}% of ${args.capital:.2f} capital)")
    print(f"Leverage:  {args.leverage}x")
    print(f"Notional:  ${notional:.2f}")
    print(f"Liquidation hits if: {100/args.leverage:.1f}% adverse move")
    print()
    print(f"This trade exposes >{args.threshold_pct}% of your capital to a single signal.")
    print(f"A 1% adverse move = ${notional*0.01:.2f} loss.")
    print(f"A 5% adverse move = ${notional*0.05:.2f} loss ({notional*0.05/args.capital*100:.1f}% capital).")
    print()

    if args.no_input:
        sys.exit(0)

    confirm = input("Type CONFIRM to proceed (anything else aborts): ").strip()
    if confirm != "CONFIRM":
        print("Aborted.")
        sys.exit(1)
    print("✓ Acknowledged — proceed at your own risk")


if __name__ == "__main__":
    main()
