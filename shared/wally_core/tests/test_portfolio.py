import pytest
from wally_core.portfolio import (
    compute_heat, would_breach, correlation_matrix, Position, HeatReport, BreachReport,
    _pearson,
)


def test_compute_heat_empty_positions():
    report = compute_heat([], 10000)
    assert report.total_heat_pct == 0
    assert report.n_positions == 0
    assert not report.breach


def test_compute_heat_single_position_with_sl():
    pos = Position(symbol="BTCUSDT", side="LONG", margin_usd=100, leverage=10,
                   entry_price=100000, sl_price=98000, qty=0.01)
    report = compute_heat([pos], 10000)
    # loss = (100000 - 98000) * 0.01 = 20 USD = 0.2% of 10000
    assert report.total_heat_pct == 0.2
    assert not report.breach


def test_compute_heat_breach():
    # 5 positions each losing 5% = 25% heat
    positions = [
        Position(symbol=f"COIN{i}", side="LONG", margin_usd=100, leverage=10,
                 entry_price=100, sl_price=95, qty=10) for i in range(5)
    ]
    report = compute_heat(positions, 10000, max_heat_pct=15.0)
    # 5 positions × (100-95)*10 = 250 USD = 2.5% — actually NOT breach
    assert report.total_heat_pct == 2.5
    assert not report.breach

    # Now make it breach: scale up
    big_positions = [
        Position(symbol=f"COIN{i}", side="LONG", margin_usd=500, leverage=10,
                 entry_price=100, sl_price=85, qty=50) for i in range(5)
    ]
    report = compute_heat(big_positions, 10000)
    # 5 × (100-85)*50 = 3750 = 37.5%
    assert report.total_heat_pct == 37.5
    assert report.breach


def test_compute_heat_no_sl_uses_5pct_default():
    pos = Position(symbol="BTCUSDT", side="LONG", margin_usd=100, leverage=10,
                   entry_price=100000, sl_price=None, qty=0.01)
    report = compute_heat([pos], 10000)
    # 5% of 100000 * 0.01 = 50 USD = 0.5%
    assert report.total_heat_pct == 0.5


def test_would_breach_heat_only():
    existing = []
    new = Position(symbol="BTCUSDT", side="LONG", margin_usd=2000, leverage=10,
                   entry_price=100, sl_price=80, qty=200)
    # potential loss = 20 * 200 = 4000 = 40% of 10000 → breach
    report = would_breach(new, existing, capital_usd=10000)
    assert report.breach
    assert report.reason == "heat_exceeded"


def test_correlation_self_is_one():
    matrix = correlation_matrix(["BTCUSDT"])
    assert matrix[("BTCUSDT", "BTCUSDT")] == 1.0


def test_pearson_uncorrelated():
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    ys = [5.0, 4.0, 3.0, 2.0, 1.0]
    # Perfect anti-correlation
    assert _pearson(xs, ys) == pytest.approx(-1.0, abs=0.01)


def test_pearson_perfect_positive():
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    ys = [2.0, 4.0, 6.0, 8.0, 10.0]
    assert _pearson(xs, ys) == pytest.approx(1.0, abs=0.01)


def test_pearson_insufficient_data_returns_zero():
    assert _pearson([1.0, 2.0], [1.0, 2.0]) == 0.0


def test_compute_heat_zero_capital():
    pos = Position(symbol="BTC", side="LONG", margin_usd=100, leverage=10,
                   entry_price=50000, sl_price=49000, qty=0.01)
    report = compute_heat([pos], capital_usd=0)
    assert report.total_heat_pct == 0
    assert not report.breach


def test_compute_heat_breakdown_fields():
    pos = Position(symbol="ETHUSDT", side="SHORT", margin_usd=50, leverage=5,
                   entry_price=3000, sl_price=3060, qty=0.1)
    report = compute_heat([pos], 10000)
    assert len(report.breakdown) == 1
    entry = report.breakdown[0]
    assert entry["symbol"] == "ETHUSDT"
    assert entry["side"] == "SHORT"
    assert entry["loss_if_sl"] == pytest.approx(6.0)  # (3060-3000)*0.1


def test_would_breach_no_existing_small_position():
    new = Position(symbol="BTCUSDT", side="LONG", margin_usd=10, leverage=10,
                   entry_price=100, sl_price=98, qty=1)
    # loss = 2 * 1 = 2 USD = 0.02% of 10000 — no breach
    report = would_breach(new, [], capital_usd=10000)
    assert not report.breach
    assert report.reason == "ok"
