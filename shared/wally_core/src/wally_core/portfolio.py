"""Portfolio risk engine — heat tracking + correlation guard for multi-position management."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import json
import urllib.request


@dataclass
class Position:
    symbol: str
    side: str  # "LONG" | "SHORT"
    margin_usd: float
    leverage: int
    entry_price: float
    sl_price: Optional[float] = None
    qty: float = 0.0


@dataclass
class HeatReport:
    total_heat_pct: float  # sum of (margin × max_loss_pct) / capital
    n_positions: int
    breach: bool  # heat > 15%
    breakdown: list[dict]  # per-position heat contribution
    capital_usd: float


def compute_heat(positions: list[Position], capital_usd: float, max_heat_pct: float = 15.0) -> HeatReport:
    """Compute portfolio heat = sum of (potential_loss_per_position) / capital.

    For each position with SL: loss = abs(entry - sl) * qty
    For each position without SL: assume 5% adverse move (conservative default).
    """
    if capital_usd <= 0:
        return HeatReport(total_heat_pct=0, n_positions=0, breach=False, breakdown=[], capital_usd=capital_usd)

    breakdown = []
    total_loss_usd = 0.0
    for p in positions:
        if p.sl_price:
            loss_per_unit = abs(p.entry_price - p.sl_price)
            position_loss = loss_per_unit * p.qty
        else:
            # Conservative: assume 5% adverse from entry
            position_loss = p.entry_price * 0.05 * p.qty

        contribution_pct = position_loss / capital_usd * 100
        total_loss_usd += position_loss
        breakdown.append({
            "symbol": p.symbol,
            "side": p.side,
            "loss_if_sl": round(position_loss, 2),
            "heat_contribution_pct": round(contribution_pct, 2),
        })

    total_heat_pct = total_loss_usd / capital_usd * 100
    return HeatReport(
        total_heat_pct=round(total_heat_pct, 2),
        n_positions=len(positions),
        breach=total_heat_pct > max_heat_pct,
        breakdown=breakdown,
        capital_usd=capital_usd,
    )


def _fetch_klines(symbol: str, interval: str = "1d", limit: int = 30) -> list[float]:
    """Fetch close prices from Binance for correlation calc. Returns empty list on error."""
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        with urllib.request.urlopen(url, timeout=10) as resp:
            bars = json.loads(resp.read())
        return [float(b[4]) for b in bars]
    except Exception:
        return []


def _pearson(xs: list[float], ys: list[float]) -> float:
    """Pearson correlation. Returns 0 on insufficient data."""
    n = min(len(xs), len(ys))
    if n < 5:
        return 0.0
    mx = sum(xs[:n]) / n
    my = sum(ys[:n]) / n
    num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    dx = sum((xs[i] - mx) ** 2 for i in range(n)) ** 0.5
    dy = sum((ys[i] - my) ** 2 for i in range(n)) ** 0.5
    if dx == 0 or dy == 0:
        return 0.0
    return num / (dx * dy)


def correlation_matrix(symbols: list[str], lookback_days: int = 30) -> dict[tuple[str, str], float]:
    """Compute pairwise correlation between symbols using daily returns.

    Returns dict[(s1, s2)] -> correlation. Self-correlation (s1==s2) returns 1.0.
    """
    closes_by_symbol = {s: _fetch_klines(s, "1d", lookback_days) for s in symbols}
    # Convert to returns
    returns_by_symbol = {}
    for s, closes in closes_by_symbol.items():
        if len(closes) < 2:
            returns_by_symbol[s] = []
        else:
            returns_by_symbol[s] = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes))]

    matrix = {}
    for s1 in symbols:
        for s2 in symbols:
            if s1 == s2:
                matrix[(s1, s2)] = 1.0
            else:
                matrix[(s1, s2)] = round(_pearson(returns_by_symbol[s1], returns_by_symbol[s2]), 3)
    return matrix


@dataclass
class BreachReport:
    breach: bool
    reason: str
    detail: dict


def would_breach(
    new_position: Position,
    existing_positions: list[Position],
    capital_usd: float,
    max_heat_pct: float = 15.0,
    max_correlation: float = 0.7,
) -> BreachReport:
    """Check if adding new_position would breach portfolio rules.

    Returns BreachReport with breach=True if:
    - Combined heat > max_heat_pct
    - Any existing position correlates > max_correlation with new_position
    """
    # Check heat
    combined = existing_positions + [new_position]
    heat = compute_heat(combined, capital_usd, max_heat_pct=max_heat_pct)
    if heat.breach:
        return BreachReport(
            breach=True,
            reason="heat_exceeded",
            detail={"total_heat_pct": heat.total_heat_pct, "max": max_heat_pct},
        )

    # Check correlations (only if existing positions present)
    if existing_positions:
        symbols = [p.symbol for p in existing_positions] + [new_position.symbol]
        matrix = correlation_matrix(symbols)
        for existing in existing_positions:
            corr = matrix.get((existing.symbol, new_position.symbol), 0.0)
            if abs(corr) > max_correlation:
                # Same direction + high correlation = concentrated risk
                if existing.side == new_position.side:
                    return BreachReport(
                        breach=True,
                        reason="correlation_concentration",
                        detail={
                            "existing": existing.symbol,
                            "new": new_position.symbol,
                            "correlation": corr,
                            "max": max_correlation,
                            "same_direction": True,
                        },
                    )

    return BreachReport(
        breach=False,
        reason="ok",
        detail={"heat_pct": heat.total_heat_pct, "n_positions": len(combined)},
    )
