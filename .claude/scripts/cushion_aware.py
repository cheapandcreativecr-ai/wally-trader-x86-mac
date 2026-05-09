#!/usr/bin/env python3
"""Cushion-aware decision logic — bias hold vs cut based on day P&L cushion + position context."""
from __future__ import annotations
import argparse
import json
from dataclasses import dataclass, asdict
from enum import Enum


class CushionDecision(str, Enum):
    HOLD_FAVORED = "HOLD_FAVORED"
    EVALUATE_NORMALLY = "EVALUATE_NORMALLY"
    CUT_FAVORED = "CUT_FAVORED"


@dataclass
class CushionResult:
    decision: CushionDecision
    score: int  # 0-100, higher = more bias to hold
    reasoning: list[str]
    metrics: dict


def cushion_score(
    *,
    day_realized_usd: float,
    position_pnl_usd: float,  # negative for losses
    liq_distance_pct: float,  # how far liquidation is, e.g. 32.0
    funding_daily_usd: float,  # cost per day to hold
    capital_total_usd: float,
    macro_thesis_aligned: bool = False,  # multi-TF supports the trade direction
) -> CushionResult:
    """Decision logic:
    - If day_realized fully absorbs position_loss × 1.5 + liq distance > 15% + funding < $1/day:
      → HOLD_FAVORED (don't cut prematurely)
    - If day_realized < -|position_loss| OR liq distance < 5% OR funding > $5/day:
      → CUT_FAVORED (urgency)
    - Otherwise → EVALUATE_NORMALLY (use standard recommendation)
    """
    reasoning = []
    metrics = {
        "day_realized_usd": day_realized_usd,
        "position_pnl_usd": position_pnl_usd,
        "liq_distance_pct": liq_distance_pct,
        "funding_daily_usd": funding_daily_usd,
        "capital_total_usd": capital_total_usd,
        "macro_thesis_aligned": macro_thesis_aligned,
    }

    # Cushion = how much profit absorbs the unrealized loss
    cushion_ratio = day_realized_usd / abs(position_pnl_usd) if position_pnl_usd < 0 else float("inf")

    score = 50  # neutral start

    # Day realized cushion
    if day_realized_usd > 0 and cushion_ratio >= 1.5:
        score += 20
        reasoning.append(f"Day realized +${day_realized_usd:.2f} absorbs loss {cushion_ratio:.1f}x → cushion strong")
    elif day_realized_usd > 0 and cushion_ratio >= 1.0:
        score += 10
        reasoning.append(f"Day realized partially absorbs loss ({cushion_ratio:.1f}x)")
    elif day_realized_usd < 0:
        score -= 15
        reasoning.append(f"Day already negative ${day_realized_usd:.2f} → no cushion")

    # Liquidation distance
    if liq_distance_pct >= 20:
        score += 15
        reasoning.append(f"Liquidation {liq_distance_pct:.1f}% away — large buffer")
    elif liq_distance_pct >= 10:
        score += 5
        reasoning.append(f"Liquidation {liq_distance_pct:.1f}% away — moderate buffer")
    elif liq_distance_pct < 5:
        score -= 30
        reasoning.append(f"Liquidation only {liq_distance_pct:.1f}% — DANGER")

    # Funding cost
    if funding_daily_usd <= 1.0:
        score += 10
        reasoning.append(f"Funding ${funding_daily_usd:.2f}/day trivial — cheap to hold")
    elif funding_daily_usd > 5.0:
        score -= 15
        reasoning.append(f"Funding ${funding_daily_usd:.2f}/day expensive — cost of waiting accumulates")

    # Macro thesis
    if macro_thesis_aligned:
        score += 10
        reasoning.append("Multi-TF thesis supports the position long-term")
    elif macro_thesis_aligned is False:
        score -= 5
        reasoning.append("No multi-TF support for this position direction")

    # Clamp score
    score = max(0, min(100, score))

    # Decide
    if score >= 65:
        decision = CushionDecision.HOLD_FAVORED
    elif score <= 35:
        decision = CushionDecision.CUT_FAVORED
    else:
        decision = CushionDecision.EVALUATE_NORMALLY

    return CushionResult(decision=decision, score=score, reasoning=reasoning, metrics=metrics)


def _cli():
    p = argparse.ArgumentParser()
    p.add_argument("--day-realized", type=float, required=True)
    p.add_argument("--position-pnl", type=float, required=True)
    p.add_argument("--liq-distance-pct", type=float, required=True)
    p.add_argument("--funding-daily", type=float, default=0.5)
    p.add_argument("--capital", type=float, required=True)
    p.add_argument("--macro-aligned", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    result = cushion_score(
        day_realized_usd=args.day_realized,
        position_pnl_usd=args.position_pnl,
        liq_distance_pct=args.liq_distance_pct,
        funding_daily_usd=args.funding_daily,
        capital_total_usd=args.capital,
        macro_thesis_aligned=args.macro_aligned,
    )

    out = asdict(result)
    out["decision"] = result.decision.value
    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print(f"Decision: {result.decision.value}  Score: {result.score}/100")
        for r in result.reasoning:
            print(f"  - {r}")


if __name__ == "__main__":
    _cli()
