import pytest
from datetime import datetime, timezone
from wally_core.signals import log_signal, close_signal_outcome, list_open_signals
from wally_core.memory import Signal, Side, SignalDecision, SignalOutcome


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(tmp_path / "profiles"))


def _sig():
    return Signal(
        ts=datetime.now(timezone.utc), profile="bitunix", source="discord",
        symbol="BTCUSDT", side=Side.LONG,
        entry=68000, sl=67500, tp1=68500, tp2=69000, tp3=70000,
        leverage=10, score=72, decision=SignalDecision.GO,
    )


def test_log_signal_returns_uuid():
    sid = log_signal(_sig())
    assert sid


def test_list_open_signals_filters_pending():
    log_signal(_sig())
    opens = list(list_open_signals("bitunix"))
    assert len(opens) == 1
    assert opens[0].outcome == SignalOutcome.PENDING


def test_close_signal_outcome_updates():
    s = _sig()
    sid = log_signal(s)
    close_signal_outcome(sid, SignalOutcome.TP1, 68500, 1.5)
    opens = list(list_open_signals("bitunix"))
    assert len(opens) == 0
