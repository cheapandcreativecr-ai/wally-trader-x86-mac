import pytest
from wally_core.calibration import compute_metrics, compare_live_vs_backtest, TradeMetrics


def test_compute_metrics_empty():
    m = compute_metrics([])
    assert m.n == 0
    assert m.wr == 0


def test_compute_metrics_basic():
    trades = [{"pnl_usd": 10}, {"pnl_usd": -5}, {"pnl_usd": 8}, {"pnl_usd": -3}]
    m = compute_metrics(trades)
    assert m.n == 4
    assert m.wr == 50.0
    # PF = (10+8) / (5+3) = 2.25
    assert m.pf == 2.25
    assert m.avg_pnl == 2.5


def test_compute_metrics_all_wins():
    trades = [{"pnl_usd": 5}, {"pnl_usd": 10}]
    m = compute_metrics(trades)
    assert m.wr == 100.0
    assert m.pf == 999.0  # capped


def test_compute_metrics_all_losses():
    trades = [{"pnl_usd": -5}, {"pnl_usd": -3}]
    m = compute_metrics(trades)
    assert m.wr == 0.0
    assert m.pf == 0.0
    assert m.avg_pnl == -4.0


def test_compute_metrics_single_trade():
    trades = [{"pnl_usd": 10}]
    m = compute_metrics(trades)
    assert m.n == 1
    assert m.wr == 100.0
    assert m.sharpe == 0  # single trade, no stdev


def test_compute_metrics_no_pnl_key():
    trades = [{"symbol": "BTC"}, {"symbol": "ETH"}]
    m = compute_metrics(trades)
    # pnl_usd defaults to 0 when key missing
    assert m.n == 2
    assert m.wr == 0


def test_compute_metrics_none_pnl_filtered():
    trades = [{"pnl_usd": None}, {"pnl_usd": 10}]
    m = compute_metrics(trades)
    # None entries filtered out of pnls
    assert m.n == 1
    assert m.wr == 100.0


def test_compute_metrics_sharpe_positive():
    trades = [{"pnl_usd": p} for p in [10, 8, 12, 9, 11]]
    m = compute_metrics(trades)
    assert m.sharpe > 0


def test_compute_metrics_max_dd():
    # Sequence: +10, -20, +5 => equity: 10, -10, -5; peak=10, dd=(10-(-10))/10=200%
    trades = [{"pnl_usd": 10}, {"pnl_usd": -20}, {"pnl_usd": 5}]
    m = compute_metrics(trades)
    assert m.max_dd_pct > 0


def test_divergence_no_drift():
    same = [{"pnl_usd": p} for p in [10, -5, 8, -3, 12, -4]]
    report = compare_live_vs_backtest(same, same)
    assert report.severity == "OK"
    assert not report.flags


def test_divergence_wr_drift_alert():
    live = [{"pnl_usd": -5}] * 8 + [{"pnl_usd": 1}] * 2  # WR 20%
    backtest = [{"pnl_usd": 5}] * 7 + [{"pnl_usd": -2}] * 3  # WR 70%
    report = compare_live_vs_backtest(live, backtest)
    # Drift: (20 - 70) / 70 = -71% > 20% threshold
    assert report.severity in ("WARN", "ALERT")
    assert any("WR drift" in f for f in report.flags)


def test_divergence_pf_drift():
    live = [{"pnl_usd": 1}] * 5 + [{"pnl_usd": -10}] * 5  # very low PF
    backtest = [{"pnl_usd": 10}] * 5 + [{"pnl_usd": -1}] * 5  # very high PF
    report = compare_live_vs_backtest(live, backtest)
    assert report.severity in ("WARN", "ALERT")


def test_divergence_severity_alert_multi_flags():
    # Both WR and PF drift will trigger
    live = [{"pnl_usd": -5}] * 9 + [{"pnl_usd": 1}]   # WR=10%, PF very low
    backtest = [{"pnl_usd": 10}] * 8 + [{"pnl_usd": -1}] * 2  # WR=80%, PF high
    report = compare_live_vs_backtest(live, backtest)
    assert report.severity == "ALERT"
    assert len(report.flags) >= 2


def test_divergence_custom_thresholds():
    # WR drift only: 60% vs 65% → drift = (60-65)/65 = -7.7%; PF same ratio kept equal
    # Use same PnL ratio so PF doesn't drift: 3 wins $10 + 2 losses $10 each
    live = [{"pnl_usd": 10}] * 6 + [{"pnl_usd": -10}] * 4  # WR=60%, PF=1.5
    backtest = [{"pnl_usd": 10}] * 65 + [{"pnl_usd": -10}] * 35  # WR=65%, PF≈1.857
    # WR drift = (60-65)/65 = -7.7%; well inside default 20% threshold
    # PF drift = (1.5 - 1.857) / 1.857 = -19.2%; inside 30% default threshold
    report_default = compare_live_vs_backtest(live, backtest)
    assert report_default.severity == "OK"
    # Tight 3% WR threshold: drift -7.7% now triggers
    report_tight = compare_live_vs_backtest(live, backtest, wr_drift_threshold_pct=3.0)
    assert report_tight.severity in ("WARN", "ALERT")


def test_divergence_drifts_are_calculated():
    live = [{"pnl_usd": 5}] * 5 + [{"pnl_usd": -5}] * 5  # WR=50%
    backtest = [{"pnl_usd": 5}] * 7 + [{"pnl_usd": -5}] * 3  # WR=70%
    report = compare_live_vs_backtest(live, backtest)
    # wr_drift = (50 - 70) / 70 * 100 = -28.57%
    assert report.wr_drift_pct < -20
    assert isinstance(report.pf_drift_pct, float)
    assert isinstance(report.sharpe_drift, float)
