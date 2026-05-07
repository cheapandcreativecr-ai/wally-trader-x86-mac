from __future__ import annotations
import csv
import os
from pathlib import Path
from typing import Iterable, Optional
from ..locking import shared_write
from .interface import MemoryBackend
from .schemas import Signal, Trade, EquityRow, JournalEntry, SignalOutcome

DEFAULT_PROFILES_DIR = Path(".claude/profiles")


class LocalBackend(MemoryBackend):
    def __init__(self, profiles_dir: Optional[Path] = None):
        self.profiles_dir = profiles_dir or Path(os.environ.get(
            "WALLY_PROFILES_DIR", str(DEFAULT_PROFILES_DIR)
        ))

    def _memory_dir(self, profile: str) -> Path:
        d = self.profiles_dir / profile / "memory"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _signals_csv(self, profile: str) -> Path:
        return self._memory_dir(profile) / "signals_received.csv"

    SIGNAL_COLS = [
        "id", "ts", "profile", "source", "symbol", "side",
        "entry", "sl", "tp1", "tp2", "tp3", "leverage",
        "score", "decision", "outcome", "exit_price", "pnl_usd", "raw_message",
    ]

    def append_signal(self, profile: str, signal: Signal) -> str:
        path = self._signals_csv(profile)
        row = signal.model_dump()
        row["ts"] = signal.ts.isoformat()
        row["side"] = signal.side.value
        row["decision"] = signal.decision.value
        row["outcome"] = signal.outcome.value
        with shared_write(path) as f:
            # Check header inside the lock so concurrent processes don't
            # each see an empty file and each write a duplicate header row.
            write_header = f.seek(0, 2) == 0  # seek to end; 0 means file is empty
            writer = csv.DictWriter(f, fieldnames=self.SIGNAL_COLS)
            if write_header:
                writer.writeheader()
            writer.writerow({k: row.get(k, "") for k in self.SIGNAL_COLS})
        return signal.id

    def update_signal_outcome(self, signal_id: str, outcome: SignalOutcome,
                              exit_price: float, pnl_usd: float) -> None:
        for prof_dir in self.profiles_dir.iterdir():
            if not prof_dir.is_dir():
                continue
            path = prof_dir / "memory" / "signals_received.csv"
            if not path.exists():
                continue
            rows = list(csv.DictReader(path.open()))
            for r in rows:
                if r.get("id") == signal_id:
                    r["outcome"] = outcome.value
                    r["exit_price"] = exit_price
                    r["pnl_usd"] = pnl_usd
                    tmp = path.with_suffix(".tmp")
                    with shared_write(tmp, mode="w") as f:
                        w = csv.DictWriter(f, fieldnames=self.SIGNAL_COLS)
                        w.writeheader()
                        for rr in rows:
                            w.writerow({k: rr.get(k, "") for k in self.SIGNAL_COLS})
                    tmp.replace(path)
                    return
        raise KeyError(f"signal {signal_id} not found")

    def read_signals(self, profile: str, *, since=None, status=None) -> Iterable[Signal]:
        path = self._signals_csv(profile)
        if not path.exists():
            return
        for r in csv.DictReader(path.open()):
            try:
                sig = Signal(
                    id=r["id"], ts=r["ts"], profile=r["profile"], source=r["source"],
                    symbol=r["symbol"], side=r["side"],
                    entry=float(r["entry"]), sl=float(r["sl"]),
                    tp1=float(r["tp1"]), tp2=float(r["tp2"]), tp3=float(r["tp3"]),
                    leverage=int(r["leverage"]), score=int(r["score"]),
                    decision=r["decision"], outcome=r["outcome"],
                    exit_price=float(r["exit_price"]) if r.get("exit_price") else None,
                    pnl_usd=float(r["pnl_usd"]) if r.get("pnl_usd") else None,
                    raw_message=r.get("raw_message", ""),
                )
            except Exception:
                continue
            if since and sig.ts.date() < since:
                continue
            if status and sig.outcome != status:
                continue
            yield sig

    def append_trade(self, profile: str, trade: Trade) -> str:
        raise NotImplementedError("Trade append arrives in Phase 5")

    def append_equity(self, profile: str, row: EquityRow) -> None:
        path = self._memory_dir(profile) / "equity_curve.csv"
        cols = ["profile", "date", "equity_usd", "equity_btc", "daily_pnl_usd", "daily_return_pct"]
        write_header = not path.exists() or path.stat().st_size == 0
        with shared_write(path) as f:
            w = csv.DictWriter(f, fieldnames=cols)
            if write_header:
                w.writeheader()
            w.writerow(row.model_dump())

    def append_journal(self, profile: str, entry: JournalEntry) -> None:
        path = self._memory_dir(profile) / "daily_journal" / f"{entry.date}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        with shared_write(path, mode="w") as f:
            f.write(f"# {entry.profile} — {entry.date}\n\n## Summary\n{entry.summary}\n\n## Lessons\n{entry.lessons}\n")

    def health_check(self) -> dict:
        return {
            "backend": "local",
            "status": "ok",
            "profiles_dir": str(self.profiles_dir),
            "writable": os.access(str(self.profiles_dir.parent), os.W_OK),
        }
