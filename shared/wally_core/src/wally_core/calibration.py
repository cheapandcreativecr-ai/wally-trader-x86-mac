"""Calibration tracker — compare live trades vs backtest expectations."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import statistics


@dataclass
class TradeMetrics:
    n: int
    wr: float  # win rate %
    pf: float  # profit factor
    sharpe: float
    max_dd_pct: float
    avg_pnl: float


@dataclass
class DivergenceReport:
    live: TradeMetrics
    backtest: TradeMetrics
    wr_drift_pct: float  # (live.wr - backtest.wr) / backtest.wr * 100
    pf_drift_pct: float
    sharpe_drift: float  # absolute delta
    severity: str  # "OK", "WARN", "ALERT"
    flags: list[str] = field(default_factory=list)


def compute_metrics(trades: list[dict]) -> TradeMetrics:
    """Compute trade metrics from list of {pnl_usd, ...} dicts."""
    if not trades:
        return TradeMetrics(n=0, wr=0, pf=0, sharpe=0, max_dd_pct=0, avg_pnl=0)

    pnls = [t.get("pnl_usd", 0) for t in trades if t.get("pnl_usd") is not None]
    if not pnls:
        return TradeMetrics(n=len(trades), wr=0, pf=0, sharpe=0, max_dd_pct=0, avg_pnl=0)

    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    wr = (len(wins) / len(pnls)) * 100 if pnls else 0
    sum_wins = sum(wins) if wins else 0
    sum_losses = abs(sum(losses)) if losses else 0
    pf = sum_wins / sum_losses if sum_losses else float("inf") if wins else 0
    avg_pnl = sum(pnls) / len(pnls)

    # Sharpe: mean / stdev (annualized would need timestamps)
    if len(pnls) > 1:
        sd = statistics.pstdev(pnls)
        sharpe = avg_pnl / sd if sd else 0
    else:
        sharpe = 0

    # Max drawdown
    cum = []
    running = 0
    for p in pnls:
        running += p
        cum.append(running)
    if cum:
        peak = cum[0]
        max_dd = 0
        for v in cum:
            if v > peak:
                peak = v
            dd = (peak - v) / abs(peak) * 100 if peak != 0 else 0
            if dd > max_dd:
                max_dd = dd
    else:
        max_dd = 0

    return TradeMetrics(
        n=len(pnls),
        wr=round(wr, 2),
        pf=round(pf, 3) if pf != float("inf") else 999.0,
        sharpe=round(sharpe, 3),
        max_dd_pct=round(max_dd, 2),
        avg_pnl=round(avg_pnl, 2),
    )


def compare_live_vs_backtest(
    live_trades: list[dict],
    backtest_trades: list[dict],
    *,
    wr_drift_threshold_pct: float = 20.0,
    pf_drift_threshold_pct: float = 30.0,
    sharpe_drift_threshold: float = 0.5,
) -> DivergenceReport:
    """Compare live vs backtest metrics, flag if drift exceeds thresholds."""
    live = compute_metrics(live_trades)
    backtest = compute_metrics(backtest_trades)

    # Drifts (handle div-by-zero)
    wr_drift = ((live.wr - backtest.wr) / backtest.wr * 100) if backtest.wr else 0
    pf_drift = ((live.pf - backtest.pf) / backtest.pf * 100) if backtest.pf else 0
    sharpe_drift = live.sharpe - backtest.sharpe

    flags = []

    if abs(wr_drift) > wr_drift_threshold_pct:
        flags.append(f"WR drift {wr_drift:+.1f}% exceeds threshold {wr_drift_threshold_pct}%")
    if abs(pf_drift) > pf_drift_threshold_pct:
        flags.append(f"PF drift {pf_drift:+.1f}% exceeds threshold {pf_drift_threshold_pct}%")
    if abs(sharpe_drift) > sharpe_drift_threshold:
        flags.append(f"Sharpe drift {sharpe_drift:+.2f} exceeds threshold {sharpe_drift_threshold}")

    if not flags:
        severity = "OK"
    elif len(flags) == 1:
        severity = "WARN"
    else:
        severity = "ALERT"

    return DivergenceReport(
        live=live,
        backtest=backtest,
        wr_drift_pct=round(wr_drift, 2),
        pf_drift_pct=round(pf_drift, 2),
        sharpe_drift=round(sharpe_drift, 3),
        severity=severity,
        flags=flags,
    )
