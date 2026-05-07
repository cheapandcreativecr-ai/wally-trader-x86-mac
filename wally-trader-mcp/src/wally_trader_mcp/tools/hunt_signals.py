"""hunt_signals tool — score bitunix watchlist and return top picks."""
import json
from pathlib import Path
from wally_core.hunt import score_asset


def hunt_signals(
    profile: str,
    watchlist: list[dict],
    regime: str = "RANGE_CHOP",
) -> dict:
    """Score each asset in the watchlist and return top 5 by score.

    Args:
        profile: must be 'bitunix' — this tool is bitunix-only
        watchlist: list of {symbol: str, bars_path: str} entries
        regime: current regime label (e.g. 'RANGE_CHOP', 'TREND_FUERTE')

    Returns:
        dict with 'top' (list of scorecards sorted descending) and 'errors' (list)
        or {'error': ..., 'profile': ...} if profile is not 'bitunix'
    """
    if profile != "bitunix":
        return {"error": "hunt_signals is bitunix-only", "profile": profile}

    results = []
    errors = []

    for asset in watchlist:
        sym = asset.get("symbol", "?")
        try:
            bars = json.loads(Path(asset["bars_path"]).read_text())
            card = score_asset(sym, bars, regime)
            results.append(
                {
                    "symbol": sym,
                    "total": card.total,
                    "momentum": card.momentum,
                    "volatility": card.volatility,
                    "trend": card.trend,
                    "volume": card.volume,
                }
            )
        except Exception as exc:
            errors.append({"symbol": sym, "error": str(exc)})

    results.sort(key=lambda r: r["total"], reverse=True)
    return {"top": results[:5], "errors": errors}
