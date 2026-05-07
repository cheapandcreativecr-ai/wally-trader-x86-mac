"""validate_setup tool — apply 4-filter Mean Reversion check."""
import json
from pathlib import Path
from wally_core.validate import validate_setup as _validate, Side


def validate_setup(bars_path: str, side: str, donchian_length: int = 15) -> dict:
    """Validate a Mean Reversion setup against the latest bar.

    Args:
        bars_path: path to JSON OHLCV bars
        side: "LONG" or "SHORT"
        donchian_length: Donchian period (default 15)

    Returns: {go: bool, reason: str, filters: [{name, passed, detail}]}
    """
    bars = json.loads(Path(bars_path).read_text())
    res = _validate(bars=bars, side=Side(side), donchian_length=donchian_length)
    return {
        "go": res.go,
        "reason": res.reason,
        "filters": [
            {"name": f.name, "passed": f.passed, "detail": f.detail}
            for f in res.filters
        ],
    }
