"""Wally Trader MCP server — exposes trading tools."""
from mcp.server.fastmcp import FastMCP

from .tools.detect_regime import detect_regime as _detect_regime
from .tools.validate_setup import validate_setup as _validate_setup
from .tools.calculate_risk import calculate_risk as _calculate_risk
from .tools.multifactor_score import multifactor_score as _multifactor_score
from .tools.macro_gate_check import macro_gate_check as _macro_gate_check
from .tools.chainlink_check import chainlink_check as _chainlink_check

mcp = FastMCP("wally-trader")


@mcp.tool()
def ping() -> dict:
    """Health check — returns server version + status."""
    return {"name": "wally-trader", "version": "0.1.0", "status": "ok"}


@mcp.tool()
def detect_regime(bars_path: str, length: int = 14) -> dict:
    """Detect market regime from OHLCV JSON file."""
    return _detect_regime(bars_path, length)


@mcp.tool()
def validate_setup(bars_path: str, side: str, donchian_length: int = 15) -> dict:
    """4-filter Mean Reversion setup validation."""
    return _validate_setup(bars_path, side, donchian_length)


@mcp.tool()
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
    """Position sizing — flat 2% / VaR / parity."""
    return _calculate_risk(profile, capital_usd, entry, sl, side, leverage, mode, bars_path)


@mcp.tool()
def multifactor_score(symbol: str, bars_path: str) -> dict:
    """Composite multifactor score (0-100)."""
    return _multifactor_score(symbol, bars_path)


@mcp.tool()
def macro_gate_check(window_min: int = 30) -> dict:
    """Check if currently within a macro event window."""
    return _macro_gate_check(window_min)


@mcp.tool()
def chainlink_check(symbol: str, current_price: float | None = None) -> dict:
    """Cross-check price against Chainlink oracle."""
    return _chainlink_check(symbol, current_price)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
