from __future__ import annotations
import json
import os
import time
from typing import Iterable, Optional
from datetime import date as _date

from .interface import MemoryBackend
from .schemas import Signal, Trade, EquityRow, JournalEntry, SignalOutcome


class NotionAPIError(Exception): ...


class NotionRateLimit(NotionAPIError): ...


class NotionBackend(MemoryBackend):
    def __init__(self, api_key: Optional[str] = None, db_ids: Optional[dict] = None):
        self.api_key = api_key or os.environ.get("NOTION_API_KEY")
        if not self.api_key:
            raise NotionAPIError("NOTION_API_KEY not set")
        if db_ids is None:
            db_ids = json.loads(os.environ.get("WALLY_NOTION_DBS", "{}"))
        self.db_ids = db_ids
        self._client = None  # lazy init

    def _client_handle(self):
        if self._client is None:
            from notion_client import Client
            self._client = Client(auth=self.api_key)
        return self._client

    def _retry(self, fn, max_retries=3):
        delay = 1
        for attempt in range(max_retries):
            try:
                return fn()
            except Exception as e:
                msg = str(e).lower()
                if "rate" in msg or "429" in msg:
                    if attempt == max_retries - 1:
                        raise NotionRateLimit(str(e))
                    time.sleep(delay)
                    delay *= 2
                else:
                    raise

    def append_signal(self, profile: str, signal: Signal) -> str:
        db_id = self.db_ids.get("signals_received")
        if not db_id:
            raise NotionAPIError("signals_received DB id not configured")
        props = {
            "ID": {"title": [{"text": {"content": signal.id}}]},
            "Source": {"select": {"name": signal.source}},
            "Symbol": {"rich_text": [{"text": {"content": signal.symbol}}]},
            "Side": {"select": {"name": signal.side.value}},
            "Entry": {"number": signal.entry},
            "SL": {"number": signal.sl},
            "TP1": {"number": signal.tp1},
            "TP2": {"number": signal.tp2},
            "TP3": {"number": signal.tp3},
            "Leverage": {"number": signal.leverage},
            "Score": {"number": signal.score},
            "Decision": {"select": {"name": signal.decision.value}},
            "Outcome": {"select": {"name": signal.outcome.value}},
            "Raw Message": {"rich_text": [{"text": {"content": signal.raw_message[:1900]}}]},
        }
        self._retry(lambda: self._client_handle().pages.create(
            parent={"database_id": db_id}, properties=props
        ))
        return signal.id

    def update_signal_outcome(self, signal_id: str, outcome: SignalOutcome,
                              exit_price: float, pnl_usd: float) -> None:
        db_id = self.db_ids["signals_received"]
        results = self._retry(lambda: self._client_handle().databases.query(
            database_id=db_id,
            filter={"property": "ID", "title": {"equals": signal_id}},
        ))
        if not results.get("results"):
            raise KeyError(f"signal {signal_id} not found in Notion")
        page_id = results["results"][0]["id"]
        self._retry(lambda: self._client_handle().pages.update(page_id=page_id, properties={
            "Outcome": {"select": {"name": outcome.value}},
            "Exit Price": {"number": exit_price},
            "PnL USD": {"number": pnl_usd},
        }))

    def read_signals(self, profile: str, *, since: Optional[_date] = None,
                     status: Optional[SignalOutcome] = None) -> Iterable[Signal]:
        db_id = self.db_ids.get("signals_received")
        if not db_id:
            return
        filt = None
        if status:
            filt = {"property": "Outcome", "select": {"equals": status.value}}
        cursor = None
        while True:
            kwargs: dict = {"database_id": db_id}
            if filt:
                kwargs["filter"] = filt
            if cursor:
                kwargs["start_cursor"] = cursor
            res = self._retry(lambda: self._client_handle().databases.query(**kwargs))
            for r in res.get("results", []):
                p = r["properties"]
                try:
                    sig = Signal(
                        id=p["ID"]["title"][0]["text"]["content"],
                        ts=r["created_time"],
                        profile=profile,
                        source=p["Source"]["select"]["name"] if p["Source"]["select"] else "discord",
                        symbol=p["Symbol"]["rich_text"][0]["text"]["content"],
                        side=p["Side"]["select"]["name"],
                        entry=p["Entry"]["number"],
                        sl=p["SL"]["number"],
                        tp1=p["TP1"]["number"],
                        tp2=p["TP2"]["number"],
                        tp3=p["TP3"]["number"],
                        leverage=int(p["Leverage"]["number"]),
                        score=int(p["Score"]["number"]),
                        decision=p["Decision"]["select"]["name"],
                        outcome=p["Outcome"]["select"]["name"] if p["Outcome"]["select"] else "pending",
                    )
                    if since and sig.ts.date() < since:
                        continue
                    yield sig
                except Exception:
                    continue
            if not res.get("has_more"):
                break
            cursor = res.get("next_cursor")

    def append_trade(self, profile: str, trade: Trade) -> str:
        raise NotImplementedError("Phase 5")

    def append_equity(self, profile: str, row: EquityRow) -> None:
        raise NotImplementedError("Phase 5")

    def append_journal(self, profile: str, entry: JournalEntry) -> None:
        raise NotImplementedError("Phase 5")

    def health_check(self) -> dict:
        try:
            db_id = self.db_ids.get("signals_received")
            if not db_id:
                return {"backend": "notion", "status": "error", "reason": "no DB id"}
            self._retry(lambda: self._client_handle().databases.retrieve(database_id=db_id))
            return {"backend": "notion", "status": "ok", "configured_dbs": list(self.db_ids.keys())}
        except Exception as e:
            return {"backend": "notion", "status": "error", "reason": str(e)}
