"""Trading journal metrics computation.

Computes Sharpe, max drawdown, IC, win rate, profit factor from a list of trades.
Uses only stdlib (statistics, math) — no numpy dependency.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Optional


@dataclass
class JournalMetrics:
    sharpe: float           # annualized Sharpe ratio (365 days/yr)
    max_dd: float           # max drawdown as percentage (0-100)
    ic: Optional[float]     # information coefficient (Pearson score vs PnL), or None
    wr: float               # win rate 0.0-1.0
    pf: float               # profit factor = sum_gains / sum_losses
    n: int                  # total trade count


def _pearson_corr(xs: list[float], ys: list[float]) -> Optional[float]:
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((xs[i] - mx) * (ys[i] - my) for i in range(len(xs)))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def _max_drawdown(equity_curve: list[float]) -> float:
    """Peak-to-trough max drawdown as a percentage (0-100)."""
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for v in equity_curve:
        if v > peak:
            peak = v
        if peak > 0:
            dd = (peak - v) / peak
            if dd > max_dd:
                max_dd = dd
    return max_dd * 100.0


def _annualized_sharpe(returns: list[float], periods_per_year: int = 365) -> float:
    if len(returns) < 2:
        return 0.0
    mu = statistics.mean(returns)
    sigma = statistics.stdev(returns)
    if sigma == 0:
        return 0.0
    return (mu / sigma) * math.sqrt(periods_per_year)


def compute_metrics(trades: list[dict]) -> JournalMetrics:
    """Compute trading metrics from a list of trade dicts.

    Each trade dict must have:
        - pnl_usd: float — realized PnL in USD
        - score: float (optional) — prediction score for IC computation
        - date: str (optional) — ignored in computation

    Returns:
        JournalMetrics dataclass.

    Raises:
        ValueError: if trades list is empty.
    """
    if not trades:
        raise ValueError("trades list is empty — need at least 1 trade")

    pnls = [float(t["pnl_usd"]) for t in trades]
    n = len(pnls)
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    wr = len(wins) / n if n else 0.0
    sum_gains = sum(wins)
    sum_losses = abs(sum(losses))
    pf = sum_gains / sum_losses if sum_losses > 0 else (math.inf if sum_gains > 0 else 0.0)

    # Equity curve starting at 0 base (relative)
    equity = [0.0]
    for p in pnls:
        equity.append(equity[-1] + p)

    max_dd = _max_drawdown(equity)

    # Per-trade returns as % change on running equity (shift by initial capital = sum of abs losses + 1 to avoid div0)
    base = max(abs(min(equity)), 1.0)
    returns = []
    for i in range(1, len(equity)):
        prev = equity[i - 1] + base
        if prev > 0:
            returns.append((equity[i] - equity[i - 1]) / prev)

    sharpe = _annualized_sharpe(returns) if len(returns) >= 2 else 0.0

    # IC: Pearson correlation between score and pnl
    paired = [(float(t["score"]), float(t["pnl_usd"]))
              for t in trades if "score" in t and t["score"] is not None]
    ic = _pearson_corr([p[0] for p in paired], [p[1] for p in paired]) if len(paired) >= 3 else None

    return JournalMetrics(
        sharpe=round(sharpe, 4),
        max_dd=round(max_dd, 4),
        ic=round(ic, 4) if ic is not None else None,
        wr=wr,
        pf=round(pf, 6) if not math.isinf(pf) else pf,
        n=n,
    )
