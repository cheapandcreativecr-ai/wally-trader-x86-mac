import pytest
from datetime import datetime, timezone
from wally_core.memory.schemas import Signal, Trade, EquityRow, JournalEntry, SignalDecision, SignalOutcome, TradeStatus, Side


def test_signal_required_fields():
    s = Signal(
        ts=datetime.now(timezone.utc),
        profile="bitunix",
        source="discord",
        symbol="BTCUSDT",
        side=Side.LONG,
        entry=68000, sl=67500, tp1=68500, tp2=69000, tp3=70000,
        leverage=10,
        score=72,
        decision=SignalDecision.GO,
    )
    assert s.outcome == SignalOutcome.PENDING


def test_signal_rejects_invalid_score_range():
    with pytest.raises(ValueError):
        Signal(
            ts=datetime.now(timezone.utc), profile="bitunix", source="discord",
            symbol="BTCUSDT", side=Side.LONG,
            entry=68000, sl=67500, tp1=68500, tp2=69000, tp3=70000,
            leverage=10, score=150, decision=SignalDecision.GO,
        )


def test_trade_status_transitions_valid():
    t = Trade(profile="retail", date="2026-05-06", asset="BTCUSDT.P",
              side=Side.LONG, entry=68000, sl=67500, tp1=68500, tp2=69000, tp3=70000,
              leverage=10, position_size_usd=20.0, status=TradeStatus.OPEN)
    assert t.id is not None
