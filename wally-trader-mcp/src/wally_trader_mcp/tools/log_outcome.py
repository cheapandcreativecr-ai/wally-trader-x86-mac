"""log_outcome tool — close an open signal's outcome."""
from wally_core.signals import close_signal_outcome
from wally_core.memory import SignalOutcome


def log_outcome(
    signal_id: str,
    outcome: str,
    exit_price: float,
    pnl_usd: float,
) -> dict:
    """Close an open signal by updating its outcome.

    Args:
        signal_id: UUID of the signal to close (returned by signal_validate)
        outcome: 'TP1' | 'TP2' | 'TP3' | 'SL' | 'manual'
        exit_price: actual exit price
        pnl_usd: realized PnL in USD (can be negative for a loss)

    Returns:
        dict with signal_id, outcome, status
    """
    close_signal_outcome(signal_id, SignalOutcome(outcome), exit_price, pnl_usd)
    return {"signal_id": signal_id, "outcome": outcome, "status": "closed"}
