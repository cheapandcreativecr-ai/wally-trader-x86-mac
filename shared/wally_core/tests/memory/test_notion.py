import os
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from wally_core.memory import Signal, Side, SignalDecision, SignalOutcome
from wally_core.memory.notion import NotionBackend, NotionAPIError, NotionRateLimit


@pytest.fixture
def backend(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "secret_TEST_KEY")
    monkeypatch.setenv("WALLY_NOTION_DBS", '{"signals_received": "test-db-id"}')
    return NotionBackend()


def _sig():
    return Signal(
        ts=datetime.now(timezone.utc),
        profile="bitunix",
        source="discord",
        symbol="BTCUSDT",
        side=Side.LONG,
        entry=68000,
        sl=67500,
        tp1=68500,
        tp2=69000,
        tp3=70000,
        leverage=10,
        score=72,
        decision=SignalDecision.GO,
    )


def test_append_signal_creates_page(backend):
    mock_client = MagicMock()
    mock_client.pages.create.return_value = {"id": "fake-page-id"}
    backend._client = mock_client
    sid = backend.append_signal("bitunix", _sig())
    assert sid
    # verify the Notion request shape
    call = mock_client.pages.create.call_args
    assert call.kwargs["parent"]["database_id"] == "test-db-id"
    props = call.kwargs["properties"]
    assert props["Side"]["select"]["name"] == "LONG"
    assert props["Score"]["number"] == 72
    assert props["Outcome"]["select"]["name"] == "pending"


def test_health_check_returns_ok_when_dbs_exist(backend):
    mock_client = MagicMock()
    mock_client.databases.retrieve.return_value = {"id": "test-db-id", "title": "..."}
    backend._client = mock_client
    h = backend.health_check()
    assert h["backend"] == "notion"
    assert h["status"] == "ok"


def test_health_check_returns_error_when_db_missing(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "secret_TEST_KEY")
    monkeypatch.setenv("WALLY_NOTION_DBS", "{}")
    backend = NotionBackend()
    h = backend.health_check()
    assert h["status"] == "error"


def test_rate_limit_triggers_backoff(backend):
    mock_client = MagicMock()
    # First two calls raise rate limit, third succeeds
    mock_client.pages.create.side_effect = [
        Exception("429 rate limit exceeded"),
        Exception("429 rate limit exceeded"),
        {"id": "fake-page-id"},
    ]
    backend._client = mock_client
    # patch sleep to avoid real waiting
    with patch("wally_core.memory.notion.time.sleep"):
        sid = backend.append_signal("bitunix", _sig())
    assert sid
    assert mock_client.pages.create.call_count == 3


def test_rate_limit_exhausts_retries(backend):
    mock_client = MagicMock()
    mock_client.pages.create.side_effect = Exception("429 rate limit")
    backend._client = mock_client
    with patch("wally_core.memory.notion.time.sleep"):
        with pytest.raises(NotionRateLimit):
            backend.append_signal("bitunix", _sig())


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    with pytest.raises(NotionAPIError):
        NotionBackend()
