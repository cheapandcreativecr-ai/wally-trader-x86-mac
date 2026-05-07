from __future__ import annotations
import os
from .interface import MemoryBackend
from .schemas import Signal, Trade, EquityRow, JournalEntry, Side, SignalDecision, SignalOutcome, TradeStatus, TradeSource


def get_backend(profile: str) -> MemoryBackend:
    """Factory — reads WALLY_MEMORY_BACKEND env or profile config.

    Default: hybrid. Falls back to local if hybrid init fails (e.g., NOTION_API_KEY missing).
    """
    backend_name = os.environ.get("WALLY_MEMORY_BACKEND", "hybrid")
    if backend_name == "local":
        from .local import LocalBackend
        return LocalBackend()
    if backend_name == "notion":
        from .notion import NotionBackend
        return NotionBackend()
    if backend_name == "hybrid":
        from .hybrid import HybridBackend
        try:
            return HybridBackend()
        except Exception:
            from .local import LocalBackend
            return LocalBackend()
    raise ValueError(f"unknown backend {backend_name}")


__all__ = ["MemoryBackend", "Signal", "Trade", "EquityRow", "JournalEntry",
           "Side", "SignalDecision", "SignalOutcome", "TradeStatus", "TradeSource",
           "get_backend"]
