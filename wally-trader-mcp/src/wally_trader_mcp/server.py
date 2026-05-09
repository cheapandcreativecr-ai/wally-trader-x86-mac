"""Wally Trader MCP server — exposes trading tools."""
from mcp.server.fastmcp import FastMCP
from typing import Optional

from .tools.detect_regime import detect_regime as _detect_regime
from .tools.validate_setup import validate_setup as _validate_setup
from .tools.calculate_risk import calculate_risk as _calculate_risk
from .tools.multifactor_score import multifactor_score as _multifactor_score
from .tools.macro_gate_check import macro_gate_check as _macro_gate_check
from .tools.chainlink_check import chainlink_check as _chainlink_check
from .tools.signal_validate import signal_validate as _signal_validate
from .tools.log_outcome import log_outcome as _log_outcome
from .tools.journal_close import journal_close as _journal_close
from .tools.hunt_signals import hunt_signals as _hunt_signals
from .tools.levels_now import levels_now as _levels_now
from .tools.macross_signal import macross_signal as _macross_signal
from .tools.portfolio_heat import portfolio_heat as _portfolio_heat
from .tools.auto_sl_tp import auto_sl_tp as _auto_sl_tp
from .tools.tilt_check import tilt_check_tool as _tilt_check
from .tools.divergence import divergence_check_tool as _divergence_check

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


@mcp.tool()
def signal_validate(
    profile: str,
    symbol: str,
    side: str,
    entry: float,
    sl: float,
    tp1: float,
    tp2: float,
    tp3: float,
    leverage: int,
    score: int,
    decision: str,
    raw_message: str = "",
    source: str = "discord",
) -> dict:
    """Validate + log a signal to the memory backend."""
    return _signal_validate(
        profile=profile, symbol=symbol, side=side,
        entry=entry, sl=sl, tp1=tp1, tp2=tp2, tp3=tp3,
        leverage=leverage, score=score, decision=decision,
        raw_message=raw_message, source=source,
    )


@mcp.tool()
def log_outcome(
    signal_id: str,
    outcome: str,
    exit_price: float,
    pnl_usd: float,
) -> dict:
    """Close an open signal's outcome (TP1/TP2/TP3/SL/manual)."""
    return _log_outcome(signal_id=signal_id, outcome=outcome,
                        exit_price=exit_price, pnl_usd=pnl_usd)


@mcp.tool()
def journal_close(
    profile: str,
    summary: str,
    lessons: str = "",
    trades: Optional[list[dict]] = None,
    equity_usd: Optional[float] = None,
    daily_pnl_usd: float = 0.0,
) -> dict:
    """Compute end-of-day metrics + append journal entry + equity row."""
    return _journal_close(
        profile=profile, summary=summary, lessons=lessons,
        trades=trades, equity_usd=equity_usd, daily_pnl_usd=daily_pnl_usd,
    )


@mcp.tool()
def hunt_signals(
    profile: str,
    watchlist: list[dict],
    regime: str = "RANGE_CHOP",
) -> dict:
    """Score bitunix watchlist assets and return top 5 picks (bitunix-only)."""
    return _hunt_signals(profile=profile, watchlist=watchlist, regime=regime)


@mcp.tool()
def levels_now(
    bars_path: str,
    donchian_length: int = 15,
    bb_length: int = 20,
    rsi_length: int = 14,
    atr_length: int = 14,
) -> dict:
    """Return current Donchian/BB/RSI/ATR levels for given OHLCV bars."""
    return _levels_now(
        bars_path=bars_path, donchian_length=donchian_length,
        bb_length=bb_length, rsi_length=rsi_length, atr_length=atr_length,
    )


@mcp.tool()
def macross_signal(
    bars_path: str,
    fast: int = 9,
    slow: int = 21,
) -> dict:
    """Detect EMA(fast)/EMA(slow) crossover signal for trending regime."""
    return _macross_signal(bars_path=bars_path, fast=fast, slow=slow)


@mcp.tool()
def portfolio_heat(positions_json: str, capital_usd: float, max_heat_pct: float = 15.0) -> dict:
    """Portfolio heat (sum of position losses / capital). Breach if heat > max_heat_pct."""
    return _portfolio_heat(positions_json, capital_usd, max_heat_pct)


@mcp.tool()
def auto_sl_tp(entry: float, side: str, atr_pct: float, regime: str = "RANGE_CHOP") -> dict:
    """Compute volatility-adjusted SL + 4 staggered TPs (R:R 2.5/4/6/8)."""
    return _auto_sl_tp(entry, side, atr_pct, regime)


@mcp.tool()
def tilt_check(
    profile: str,
    recent_trades_json: str = "[]",
    cooldown_file: str = ".claude/cache/cooldowns.json",
) -> dict:
    """Tilt detection + cooldown status for a profile."""
    return _tilt_check(profile, recent_trades_json, cooldown_file)


@mcp.tool()
def divergence_check(profile: str, window_days: int = 30) -> dict:
    """Live vs backtest calibration divergence."""
    return _divergence_check(profile, window_days)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
