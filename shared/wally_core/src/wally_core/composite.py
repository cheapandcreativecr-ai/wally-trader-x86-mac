"""Composite signal score — combines all confluences into single 0-100 grade."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SignalGrade(str, Enum):
    A_PLUS = "A+"  # 90-100
    A = "A"  # 80-89
    B = "B"  # 65-79
    C = "C"  # 50-64
    F = "F"  # <50


@dataclass
class CompositeScoreResult:
    score: int  # 0-100
    grade: SignalGrade
    breakdown: dict  # each component score
    veto_reasons: list[str] = field(default_factory=list)  # hard rejections
    recommended_size_multiplier: float = 1.0  # 0.5x for B, 1.0x for A, 1.5x for A+


def composite_signal_score(
    *,
    multifactor_score: int,  # 0-100 from wally_core.multifactor
    regime_aligned: bool,  # does the side match what regime_mapping recommends?
    ml_score: Optional[int] = None,  # 0-100 from XGBoost, None if unavailable
    sentiment_score: int = 50,  # 0-100, 50 neutral
    macro_clear: bool = True,  # macro_gate_check returns no event in window
    smart_router_decision: str = "no_setup",  # approved/no_setup/vetoed/stand_aside
) -> CompositeScoreResult:
    """Weighted composite:
    - 25% multifactor
    - 20% regime alignment (binary 0 or 100)
    - 20% ml score (default 50 if unavailable)
    - 15% sentiment
    - 10% macro clear (binary 0 or 100)
    - 10% smart router (approved=100, no_setup=50, vetoed=20, stand_aside=0)

    Hard vetoes:
    - macro_clear=False → score capped at 50
    - smart_router='vetoed' → score capped at 40
    - smart_router='stand_aside' AND regime_aligned=False → score capped at 30
    """
    breakdown = {}
    veto_reasons = []

    # Components
    breakdown["multifactor"] = multifactor_score
    breakdown["regime_aligned"] = 100 if regime_aligned else 0
    breakdown["ml"] = ml_score if ml_score is not None else 50
    breakdown["sentiment"] = sentiment_score
    breakdown["macro_clear"] = 100 if macro_clear else 0

    sr_score = {
        "approved": 100,
        "no_setup": 50,
        "vetoed": 20,
        "stand_aside": 0,
    }.get(smart_router_decision, 50)
    breakdown["smart_router"] = sr_score

    # Weighted
    score = round(
        0.25 * multifactor_score
        + 0.20 * breakdown["regime_aligned"]
        + 0.20 * breakdown["ml"]
        + 0.15 * sentiment_score
        + 0.10 * breakdown["macro_clear"]
        + 0.10 * sr_score
    )

    # Apply hard caps
    if not macro_clear:
        veto_reasons.append("macro_event_in_window")
        score = min(score, 50)
    if smart_router_decision == "vetoed":
        veto_reasons.append("smart_router_vetoed")
        score = min(score, 40)
    if smart_router_decision == "stand_aside" and not regime_aligned:
        veto_reasons.append("stand_aside_and_counter_trend")
        score = min(score, 30)

    # Grade
    if score >= 90:
        grade = SignalGrade.A_PLUS
        size_mult = 1.5
    elif score >= 80:
        grade = SignalGrade.A
        size_mult = 1.0
    elif score >= 65:
        grade = SignalGrade.B
        size_mult = 0.5
    elif score >= 50:
        grade = SignalGrade.C
        size_mult = 0.25
    else:
        grade = SignalGrade.F
        size_mult = 0.0

    return CompositeScoreResult(
        score=score,
        grade=grade,
        breakdown=breakdown,
        veto_reasons=veto_reasons,
        recommended_size_multiplier=size_mult,
    )
