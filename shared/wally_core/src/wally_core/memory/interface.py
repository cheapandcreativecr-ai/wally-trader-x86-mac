from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import date
from typing import Iterable, Optional
from .schemas import Signal, Trade, EquityRow, JournalEntry, SignalOutcome


class MemoryBackend(ABC):
    @abstractmethod
    def append_signal(self, profile: str, signal: Signal) -> str: ...

    @abstractmethod
    def update_signal_outcome(self, signal_id: str, outcome: SignalOutcome,
                              exit_price: float, pnl_usd: float) -> None: ...

    @abstractmethod
    def read_signals(self, profile: str, *, since: Optional[date] = None,
                     status: Optional[SignalOutcome] = None) -> Iterable[Signal]: ...

    @abstractmethod
    def append_trade(self, profile: str, trade: Trade) -> str: ...

    @abstractmethod
    def append_equity(self, profile: str, row: EquityRow) -> None: ...

    @abstractmethod
    def append_journal(self, profile: str, entry: JournalEntry) -> None: ...

    @abstractmethod
    def health_check(self) -> dict: ...
