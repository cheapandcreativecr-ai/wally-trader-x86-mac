from __future__ import annotations
from datetime import datetime, date as _date
from enum import Enum
from typing import Optional
from uuid import uuid4
from pydantic import BaseModel, Field, field_validator


class Side(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class SignalDecision(str, Enum):
    GO = "GO"
    NO_GO = "NO-GO"
    WARN = "WARN"


class SignalOutcome(str, Enum):
    TP1 = "TP1"
    TP2 = "TP2"
    TP3 = "TP3"
    SL = "SL"
    MANUAL = "manual"
    PENDING = "pending"


class TradeStatus(str, Enum):
    OPEN = "open"
    TP1_HIT = "tp1_hit"
    TP2_HIT = "tp2_hit"
    TP3_HIT = "tp3_hit"
    SL = "sl"
    CLOSED_MANUAL = "closed_manual"


class TradeSource(str, Enum):
    MANUAL = "manual"
    SIGNAL = "signal"
    HUNT = "hunt"
    COPY = "copy"


class Signal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    ts: datetime
    profile: str
    source: str
    symbol: str
    side: Side
    entry: float
    sl: float
    tp1: float
    tp2: float
    tp3: float
    leverage: int
    score: int = Field(ge=0, le=100)
    decision: SignalDecision
    outcome: SignalOutcome = SignalOutcome.PENDING
    exit_price: Optional[float] = None
    pnl_usd: Optional[float] = None
    raw_message: str = ""


class Trade(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    profile: str
    date: str
    asset: str
    side: Side
    entry: float
    sl: float
    tp1: float
    tp2: float
    tp3: float
    leverage: int
    position_size_usd: float
    exit_price: Optional[float] = None
    pnl_usd: float = 0.0
    pnl_pct: float = 0.0
    r_multiple: float = 0.0
    status: TradeStatus
    source: TradeSource = TradeSource.MANUAL
    notes: str = ""


class EquityRow(BaseModel):
    profile: str
    date: str
    equity_usd: float
    equity_btc: Optional[float] = None
    daily_pnl_usd: float
    daily_return_pct: float


class JournalEntry(BaseModel):
    profile: str
    date: str
    summary: str
    lessons: str = ""
    screenshots: list[str] = Field(default_factory=list)
