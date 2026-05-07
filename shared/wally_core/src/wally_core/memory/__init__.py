from __future__ import annotations
from .interface import MemoryBackend
from .schemas import Signal, Trade, EquityRow, JournalEntry, Side, SignalDecision, SignalOutcome, TradeStatus, TradeSource


def get_backend(profile: str) -> MemoryBackend:
    """Factory — reads profile config to choose backend.

    For now (Phase 2), always returns LocalBackend. Phase 4 will read profile config.
    """
    from .local import LocalBackend
    return LocalBackend()


__all__ = ["MemoryBackend", "Signal", "Trade", "EquityRow", "JournalEntry",
           "Side", "SignalDecision", "SignalOutcome", "TradeStatus", "TradeSource",
           "get_backend"]
