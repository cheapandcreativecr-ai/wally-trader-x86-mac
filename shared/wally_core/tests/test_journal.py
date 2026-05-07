"""Tests for wally_core.journal — trading metrics computation."""
import pytest
from wally_core.journal import compute_metrics, JournalMetrics


# Synthetic trades: 3 wins, 2 losses
TRADES_WINNING = [
    {"date": "2026-05-01", "pnl_usd": 5.0, "score": 80},
    {"date": "2026-05-02", "pnl_usd": -2.0, "score": 40},
    {"date": "2026-05-03", "pnl_usd": 3.0, "score": 75},
    {"date": "2026-05-04", "pnl_usd": -1.5, "score": 35},
    {"date": "2026-05-05", "pnl_usd": 4.0, "score": 82},
]

# All losses
TRADES_LOSING = [
    {"date": "2026-05-01", "pnl_usd": -2.0},
    {"date": "2026-05-02", "pnl_usd": -3.0},
    {"date": "2026-05-03", "pnl_usd": -1.0},
]


# ── Test 1: win rate computed correctly ───────────────────────────────────────

def test_win_rate_matches_manual_count():
    m = compute_metrics(TRADES_WINNING)
    assert m.n == 5
    assert abs(m.wr - 0.60) < 1e-9  # 3 wins / 5 trades


# ── Test 2: profit factor matches manual sum ──────────────────────────────────

def test_profit_factor_matches_manual_sum():
    m = compute_metrics(TRADES_WINNING)
    # sum gains = 5+3+4=12, sum losses abs = 2+1.5=3.5
    expected_pf = 12.0 / 3.5
    assert abs(m.pf - expected_pf) < 1e-4  # tolerates rounding in float repr


# ── Test 3: sharpe positive on winning set, negative on losing set ─────────────

def test_sharpe_positive_on_winning_set():
    m = compute_metrics(TRADES_WINNING)
    assert m.sharpe > 0


def test_sharpe_negative_on_losing_set():
    m = compute_metrics(TRADES_LOSING)
    assert m.sharpe < 0


# ── Test 4: IC computed when score present, None when absent ──────────────────

def test_ic_computed_when_score_present():
    m = compute_metrics(TRADES_WINNING)
    # 5 trades have scores, should produce a correlation
    assert m.ic is not None
    assert -1.0 <= m.ic <= 1.0


def test_ic_none_when_no_score_column():
    trades_no_score = [{"date": "2026-05-01", "pnl_usd": v}
                       for v in [2.0, -1.0, 3.0, -1.5, 4.0]]
    m = compute_metrics(trades_no_score)
    assert m.ic is None


# ── Test 5: empty trades raises ValueError ────────────────────────────────────

def test_empty_trades_raises():
    with pytest.raises(ValueError, match="empty"):
        compute_metrics([])
