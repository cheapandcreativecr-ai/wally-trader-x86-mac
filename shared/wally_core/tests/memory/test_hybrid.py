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


def test_sync_pull_imports_remote_signals(tmp_path, monkeypatch):
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(tmp_path / "profiles"))
    monkeypatch.setenv("NOTION_API_KEY", "secret_test")
    monkeypatch.setenv("WALLY_NOTION_DBS", '{"signals_received": "fake-db"}')
    from wally_core.memory.hybrid import HybridBackend
    h = HybridBackend()
    h.notion_offline = False  # force online for this test
    # build 2 signals "in Notion" via mocked notion backend
    fake_sigs = [
        Signal(ts=datetime.now(timezone.utc), profile="bitunix", source="discord",
               symbol="BTC", side=Side.LONG, entry=68000 + i, sl=67500,
               tp1=68500, tp2=69000, tp3=70000, leverage=10, score=70 + i,
               decision=SignalDecision.GO)
        for i in range(2)
    ]
    fake_notion = type("FakeNotion", (), {})()
    fake_notion.read_signals = lambda profile, **kw: iter(fake_sigs)
    h._notion = fake_notion
    n = h.sync_pull("bitunix")
    assert n == 2
    local_sigs = list(h.local.read_signals("bitunix"))
    assert len(local_sigs) == 2


def test_sync_pull_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(tmp_path / "profiles"))
    monkeypatch.setenv("NOTION_API_KEY", "secret_test")
    monkeypatch.setenv("WALLY_NOTION_DBS", '{"signals_received": "fake-db"}')
    from wally_core.memory.hybrid import HybridBackend
    h = HybridBackend()
    h.notion_offline = False
    sig = Signal(ts=datetime.now(timezone.utc), profile="bitunix", source="discord",
                 symbol="BTC", side=Side.LONG, entry=68000, sl=67500,
                 tp1=68500, tp2=69000, tp3=70000, leverage=10, score=70,
                 decision=SignalDecision.GO)
    # Pre-populate local with the same UUID
    h.local.append_signal("bitunix", sig)
    fake_notion = type("FakeNotion", (), {})()
    fake_notion.read_signals = lambda profile, **kw: iter([sig])
    h._notion = fake_notion
    n = h.sync_pull("bitunix")
    assert n == 0  # already exists
