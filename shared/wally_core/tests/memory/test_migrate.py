import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from wally_core.memory.schemas import Signal, Side, SignalDecision


@pytest.fixture
def populated_local(tmp_path, monkeypatch):
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(tmp_path / "profiles"))
    from wally_core.memory.local import LocalBackend
    b = LocalBackend()
    for i in range(3):
        b.append_signal("bitunix", Signal(
            ts=datetime.now(timezone.utc), profile="bitunix", source="discord",
            symbol=f"BTCUSDT-{i}", side=Side.LONG,
            entry=68000+i, sl=67500, tp1=68500, tp2=69000, tp3=70000,
            leverage=10, score=70+i, decision=SignalDecision.GO,
        ))
    return tmp_path


def test_migrate_dry_run_does_not_call_notion(populated_local):
    from wally_core.memory.migrate import migrate_profile
    res = migrate_profile("bitunix", dry_run=True)
    assert res["would_migrate"] == 3
    assert res["actually_migrated"] == 0


def test_migrate_uploads_signals(populated_local, monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "secret_TEST")
    monkeypatch.setenv("WALLY_NOTION_DBS", '{"signals_received": "test-db-id"}')
    # Mock NotionBackend's notion-client interactions
    from wally_core.memory import notion as notion_mod
    mock_client = MagicMock()
    mock_client.pages.create.return_value = {"id": "fake"}
    mock_client.databases.query.return_value = {"results": [], "has_more": False}
    with patch.object(notion_mod.NotionBackend, "_client_handle", lambda self: mock_client):
        from wally_core.memory.migrate import migrate_profile
        res = migrate_profile("bitunix", dry_run=False)
    assert res["actually_migrated"] == 3
    assert res["skipped"] == 0


def test_migrate_idempotent_skips_existing(populated_local, monkeypatch):
    """
    Directly patches NotionBackend.read_signals to return Signal objects with the
    same UUIDs already in local CSV, verifying that migrate_profile skips them all.
    We patch at the method level rather than mocking the SDK pagination because the
    goal is to verify idempotency logic (UUID set diff), not to re-test SDK behaviour
    which is already covered in test_notion.py.
    """
    monkeypatch.setenv("NOTION_API_KEY", "secret_TEST")
    monkeypatch.setenv("WALLY_NOTION_DBS", '{"signals_received": "test-db-id"}')

    # Get the local signals so we know their UUIDs
    from wally_core.memory.local import LocalBackend
    local_sigs = list(LocalBackend().read_signals("bitunix"))
    existing_ids = [s.id for s in local_sigs]
    assert len(existing_ids) == 3

    from wally_core.memory import notion as notion_mod
    mock_client = MagicMock()
    mock_client.pages.create.return_value = {"id": "fake"}

    with patch.object(notion_mod.NotionBackend, "_client_handle", lambda self: mock_client):
        # Patch read_signals to return the local signals (simulating they're already in Notion)
        with patch.object(notion_mod.NotionBackend, "read_signals", return_value=iter(local_sigs)):
            from wally_core.memory.migrate import migrate_profile
            res = migrate_profile("bitunix", dry_run=False)

    assert res["actually_migrated"] == 0
    assert res["skipped"] == 3
    # Verify pages.create was never called
    mock_client.pages.create.assert_not_called()
