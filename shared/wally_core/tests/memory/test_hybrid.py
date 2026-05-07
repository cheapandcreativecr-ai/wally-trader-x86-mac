import json
import pytest
from datetime import datetime, timezone
from wally_core.memory.schemas import Signal, Side, SignalDecision


@pytest.fixture
def hybrid(tmp_path, monkeypatch):
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(tmp_path / "profiles"))
    monkeypatch.setenv("NOTION_API_KEY", "secret_test")
    monkeypatch.setenv("WALLY_NOTION_DBS", '{"signals_received": "fake-db"}')
    from wally_core.memory.hybrid import HybridBackend
    return HybridBackend(notion_offline=True)


def _sig():
    return Signal(
        ts=datetime.now(timezone.utc), profile="bitunix", source="discord",
        symbol="BTCUSDT", side=Side.LONG,
        entry=68000, sl=67500, tp1=68500, tp2=69000, tp3=70000,
        leverage=10, score=72, decision=SignalDecision.GO,
    )


def test_hybrid_writes_locally_and_enqueues_for_notion(hybrid, tmp_path):
    sid = hybrid.append_signal("bitunix", _sig())
    csv_path = tmp_path / "profiles" / "bitunix" / "memory" / "signals_received.csv"
    queue_path = tmp_path / "profiles" / "bitunix" / "memory" / ".notion_pending.jsonl"
    assert csv_path.exists()
    assert queue_path.exists()
    assert sum(1 for _ in queue_path.open()) == 1


def test_hybrid_reads_from_local_first(hybrid):
    sid = hybrid.append_signal("bitunix", _sig())
    sigs = list(hybrid.read_signals("bitunix"))
    assert any(s.id == sid for s in sigs)


def test_hybrid_health_reports_queue_depth(hybrid):
    hybrid.append_signal("bitunix", _sig())
    hybrid.append_signal("bitunix", _sig())
    h = hybrid.health_check()
    assert h["backend"] == "hybrid"
    assert h["queue_depth"]["bitunix"] == 2
