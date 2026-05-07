from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Iterable, Optional
from .interface import MemoryBackend
from .schemas import Signal, Trade, EquityRow, JournalEntry, SignalOutcome
from .local import LocalBackend
from ..locking import shared_write


class HybridBackend(MemoryBackend):
    def __init__(self, notion_offline: bool = False):
        self.local = LocalBackend()
        self.notion_offline = notion_offline
        self._notion = None  # lazy

    def _notion_handle(self):
        if self.notion_offline:
            return None
        if self._notion is None:
            from .notion import NotionBackend
            try:
                self._notion = NotionBackend()
            except Exception:
                self.notion_offline = True
                return None
        return self._notion

    def _queue_path(self, profile: str) -> Path:
        return self.local._memory_dir(profile) / ".notion_pending.jsonl"

    def _enqueue(self, profile: str, op: dict):
        with shared_write(self._queue_path(profile)) as f:
            f.write(json.dumps(op) + "\n")

    def append_signal(self, profile: str, signal: Signal) -> str:
        sid = self.local.append_signal(profile, signal)
        self._enqueue(profile, {
            "op": "append_signal",
            "profile": profile,
            "signal": signal.model_dump(mode="json"),
        })
        if not self.notion_offline:
            self._drain(profile)
        return sid

    def update_signal_outcome(self, signal_id: str, outcome: SignalOutcome,
                              exit_price: float, pnl_usd: float) -> None:
        self.local.update_signal_outcome(signal_id, outcome, exit_price, pnl_usd)
        for prof_dir in self.local.profiles_dir.iterdir():
            if not prof_dir.is_dir():
                continue
            for s in self.local.read_signals(prof_dir.name):
                if s.id == signal_id:
                    self._enqueue(prof_dir.name, {
                        "op": "update_signal_outcome",
                        "signal_id": signal_id,
                        "outcome": outcome.value,
                        "exit_price": exit_price,
                        "pnl_usd": pnl_usd,
                    })
                    if not self.notion_offline:
                        self._drain(prof_dir.name)
                    return
        raise KeyError(signal_id)

    def read_signals(self, profile: str, *, since=None, status=None) -> Iterable[Signal]:
        yield from self.local.read_signals(profile, since=since, status=status)

    def append_trade(self, profile: str, trade: Trade) -> str:
        raise NotImplementedError("Phase 5")

    def append_equity(self, profile: str, row: EquityRow) -> None:
        self.local.append_equity(profile, row)
        self._enqueue(profile, {"op": "append_equity", "profile": profile, "row": row.model_dump()})
        if not self.notion_offline:
            self._drain(profile)

    def append_journal(self, profile: str, entry: JournalEntry) -> None:
        self.local.append_journal(profile, entry)
        self._enqueue(profile, {"op": "append_journal", "profile": profile, "entry": entry.model_dump()})
        if not self.notion_offline:
            self._drain(profile)

    def _drain(self, profile: str):
        notion = self._notion_handle()
        if notion is None:
            return
        qpath = self._queue_path(profile)
        if not qpath.exists() or qpath.stat().st_size == 0:
            return
        ops = []
        with qpath.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    ops.append(json.loads(line))
        remaining = []
        for op in ops:
            try:
                if op["op"] == "append_signal":
                    sig = Signal(**op["signal"])
                    notion.append_signal(op["profile"], sig)
                elif op["op"] == "update_signal_outcome":
                    notion.update_signal_outcome(
                        op["signal_id"], SignalOutcome(op["outcome"]),
                        op["exit_price"], op["pnl_usd"],
                    )
            except Exception:
                remaining.append(op)
        tmp = qpath.with_suffix(".tmp")
        with shared_write(tmp, mode="w") as f:
            for op in remaining:
                f.write(json.dumps(op) + "\n")
        tmp.replace(qpath)

    def health_check(self) -> dict:
        depths = {}
        for prof_dir in self.local.profiles_dir.glob("*"):
            if not prof_dir.is_dir():
                continue
            qpath = self._queue_path(prof_dir.name)
            if qpath.exists():
                depths[prof_dir.name] = sum(1 for _ in qpath.open())
        return {
            "backend": "hybrid",
            "status": "ok" if not self.notion_offline else "degraded",
            "queue_depth": depths,
            "notion_online": not self.notion_offline,
        }
