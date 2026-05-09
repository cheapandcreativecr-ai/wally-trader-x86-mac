"""Portfolio heat MCP tool wrapper."""
import json
from wally_core.portfolio import compute_heat, would_breach, Position


def portfolio_heat(positions_json: str, capital_usd: float, max_heat_pct: float = 15.0) -> dict:
    """Compute portfolio heat from JSON positions list.

    positions_json: JSON array of {symbol, side, margin_usd, leverage, entry_price, sl_price, qty}
    """
    positions_data = json.loads(positions_json) if isinstance(positions_json, str) else positions_json
    positions = [Position(**p) for p in positions_data]
    report = compute_heat(positions, capital_usd, max_heat_pct=max_heat_pct)
    return {
        "total_heat_pct": report.total_heat_pct,
        "n_positions": report.n_positions,
        "breach": report.breach,
        "breakdown": report.breakdown,
        "capital_usd": report.capital_usd,
    }
