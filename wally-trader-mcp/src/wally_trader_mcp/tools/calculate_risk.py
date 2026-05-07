"""calculate_risk tool — flat 2% / VaR / parity sizing."""
import json
from pathlib import Path
from wally_core.risk import calculate_position_size, RiskMode


def calculate_risk(
    profile: str,
    capital_usd: float,
    entry: float,
    sl: float,
    side: str,
    leverage: int,
    mode: str = "flat_2pct",
    bars_path: str | None = None,
) -> dict:
    """Compute position size + margin + warnings.

    mode: 'flat_2pct' | 'var' | 'parity'
    """
    bars = None
    if mode == "var" and bars_path:
        bars = json.loads(Path(bars_path).read_text())
    res = calculate_position_size(
        capital_usd=capital_usd,
        entry=entry,
        sl=sl,
        side=side,
        leverage=leverage,
        mode=RiskMode(mode),
        profile=profile,
        bars_for_var=bars,
    )
    return {
        "risk_usd": res.risk_usd,
        "position_size_btc": res.position_size_btc,
        "margin_usd": res.margin_usd,
        "leverage_used": res.leverage_used,
        "mode": res.mode.value,
        "warnings": res.warnings,
        "var_pct": res.var_pct,
    }
