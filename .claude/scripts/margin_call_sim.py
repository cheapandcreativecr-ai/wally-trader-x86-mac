#!/usr/bin/env python3
"""Margin call simulator — show liq price, MFE/MAE estimates."""
import sys
import argparse


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--entry", type=float, required=True)
    p.add_argument("--leverage", type=int, required=True)
    p.add_argument("--side", choices=["LONG", "SHORT"], required=True)
    p.add_argument("--maintenance-margin-pct", type=float, default=0.5,
                   help="Bitunix-typical maintenance margin, default 0.5")
    args = p.parse_args()

    # Simplified linear liquidation calc (ignores fees + funding)
    initial_margin_pct = 100 / args.leverage  # e.g., 10x → 10%
    liquidation_buffer = initial_margin_pct - args.maintenance_margin_pct
    liq_distance_pct = liquidation_buffer  # adverse move % to liq

    if args.side == "LONG":
        liq_price = args.entry * (1 - liq_distance_pct / 100)
    else:
        liq_price = args.entry * (1 + liq_distance_pct / 100)

    print(f"=== Margin Call Simulator ===")
    print(f"Entry: ${args.entry}  |  Side: {args.side}  |  Leverage: {args.leverage}x")
    print(f"Initial margin: {initial_margin_pct:.2f}%  |  Maintenance: {args.maintenance_margin_pct:.2f}%")
    print(f"Liquidation buffer: {liquidation_buffer:.2f}%")
    print(f"Estimated LIQ price: ${liq_price:.6f}  ({liq_distance_pct:.2f}% adverse from entry)")
    print()
    print("MFE/MAE table (% adverse move → P&L on $100 margin):")
    for adverse_pct in [1, 2, 3, 5, 7, 10, liquidation_buffer]:
        if adverse_pct >= liquidation_buffer:
            print(f"  {adverse_pct:.2f}%: LIQUIDATION — full margin loss")
            break
        else:
            loss_pct_margin = adverse_pct / initial_margin_pct * 100
            print(f"  {adverse_pct:.2f}% adverse: lose {loss_pct_margin:.0f}% of margin ($-{loss_pct_margin:.2f}/100)")


if __name__ == "__main__":
    main()
