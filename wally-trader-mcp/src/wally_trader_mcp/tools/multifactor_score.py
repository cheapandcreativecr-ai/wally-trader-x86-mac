"""multifactor_score tool — composite 0-100 score over OHLCV bars."""
import json
from pathlib import Path
from wally_core.multifactor import composite_score


def multifactor_score(symbol: str, bars_path: str) -> dict:
    """Compute composite multifactor score (0-100) for symbol's bars.

    composite_score returns an integer 0-100.

    Returns: {symbol, score}
    """
    bars = json.loads(Path(bars_path).read_text())
    score = composite_score(symbol=symbol, bars=bars)
    # composite_score returns int; wrap in standard dict
    if isinstance(score, dict):
        return {"symbol": symbol, **score}
    return {"symbol": symbol, "score": int(score)}
