import pytest
from wally_core.composite import composite_signal_score, SignalGrade


def test_composite_a_plus_grade():
    res = composite_signal_score(
        multifactor_score=85, regime_aligned=True, ml_score=85,
        sentiment_score=80, macro_clear=True, smart_router_decision="approved",
    )
    assert res.score >= 80
    assert res.grade in (SignalGrade.A, SignalGrade.A_PLUS)


def test_composite_macro_event_caps_score():
    res = composite_signal_score(
        multifactor_score=95, regime_aligned=True, ml_score=95,
        sentiment_score=95, macro_clear=False, smart_router_decision="approved",
    )
    assert res.score <= 50
    assert "macro_event_in_window" in res.veto_reasons


def test_composite_stand_aside_counter_trend():
    res = composite_signal_score(
        multifactor_score=75, regime_aligned=False, ml_score=70,
        sentiment_score=70, macro_clear=True, smart_router_decision="stand_aside",
    )
    assert res.score <= 30


def test_composite_grade_thresholds():
    assert composite_signal_score(multifactor_score=95, regime_aligned=True, ml_score=95, sentiment_score=95).score >= 90
    assert composite_signal_score(multifactor_score=70, regime_aligned=True, ml_score=70, sentiment_score=70).grade == SignalGrade.B


def test_composite_vetoed_caps_at_40():
    res = composite_signal_score(
        multifactor_score=90, regime_aligned=True, ml_score=90,
        sentiment_score=90, macro_clear=True, smart_router_decision="vetoed",
    )
    assert res.score <= 40
    assert "smart_router_vetoed" in res.veto_reasons


def test_composite_no_ml_uses_neutral():
    res_with = composite_signal_score(multifactor_score=70, regime_aligned=True, ml_score=50)
    res_without = composite_signal_score(multifactor_score=70, regime_aligned=True, ml_score=None)
    assert res_with.score == res_without.score


def test_composite_f_grade_zero_multiplier():
    res = composite_signal_score(
        multifactor_score=10, regime_aligned=False, ml_score=10,
        sentiment_score=10, macro_clear=False, smart_router_decision="vetoed",
    )
    assert res.grade == SignalGrade.F
    assert res.recommended_size_multiplier == 0.0


def test_composite_a_plus_grade_high_multiplier():
    res = composite_signal_score(
        multifactor_score=95, regime_aligned=True, ml_score=95,
        sentiment_score=95, macro_clear=True, smart_router_decision="approved",
    )
    assert res.grade == SignalGrade.A_PLUS
    assert res.recommended_size_multiplier == 1.5
