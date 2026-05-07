"""High-level signal helpers — thin delegation to the memory backend."""
from __future__ import annotations

from typing import Iterable

from .memory import get_backend, Signal, SignalOutcome


def log_signal(signal: Signal) -> str:
    """Persist a new signal and return its UUID."""
    return get_backend(signal.profile).append_signal(signal.profile, signal)


def close_signal_outcome(
    signal_id: str,
    outcome: SignalOutcome,
    exit_price: float,
    pnl_usd: float,
) -> None:
    """Update outcome for a previously logged signal (searches all profiles)."""
    get_backend("default").update_signal_outcome(signal_id, outcome, exit_price, pnl_usd)


def list_open_signals(profile: str) -> Iterable[Signal]:
    """Yield all PENDING signals for the given profile."""
    yield from get_backend(profile).read_signals(profile, status=SignalOutcome.PENDING)
