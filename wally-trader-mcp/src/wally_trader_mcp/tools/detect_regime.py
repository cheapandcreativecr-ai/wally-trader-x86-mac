"""detect_regime tool — read OHLCV JSON, return ADX + regime label."""
import json
from pathlib import Path
from wally_core.regime import compute_adx, label_regime


def detect_regime(bars_path: str, length: int = 14) -> dict:
    """Detect market regime from OHLCV bars JSON file.

    Args:
        bars_path: path to JSON file with list of {open, high, low, close, volume} dicts
        length: ADX smoothing length (default 14)

    Returns: dict with adx, plus_di, minus_di, label
    """
    bars = json.loads(Path(bars_path).read_text())
    res = compute_adx(bars, length=length)
    label = label_regime(res["adx"], res["plus_di"], res["minus_di"])
    return {**res, "label": label.value}
