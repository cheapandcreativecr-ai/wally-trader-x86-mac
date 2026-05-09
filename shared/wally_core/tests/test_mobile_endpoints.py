import os
import secrets
import pytest
from pathlib import Path
from fastapi.testclient import TestClient


@pytest.fixture
def client_with_token(tmp_path, monkeypatch):
    profiles_dir = tmp_path / "profiles"
    bitunix_mem = profiles_dir / "bitunix" / "memory"
    bitunix_mem.mkdir(parents=True)
    (bitunix_mem / "signals_received.csv").write_text(
        "ts,symbol,side\n2026-05-08T12:00:00+00:00,BTC,LONG\n"
    )
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(profiles_dir))
    monkeypatch.setenv("HOME", str(tmp_path))  # so ~/.wally/ goes to tmp

    from wally_core.dashboard_server import app, _ensure_mobile_token
    token = _ensure_mobile_token()
    return TestClient(app), token


def test_mobile_dashboard_requires_auth(client_with_token):
    client, token = client_with_token
    # Without token -> 401
    r = client.get("/api/v1/mobile/dashboard")
    assert r.status_code == 401


def test_mobile_dashboard_with_valid_token(client_with_token):
    client, token = client_with_token
    r = client.get("/api/v1/mobile/dashboard", headers={"X-Api-Key": token})
    assert r.status_code == 200
    body = r.json()
    assert "profiles" in body


def test_mobile_positions_requires_auth(client_with_token):
    client, token = client_with_token
    r = client.get("/api/v1/mobile/positions")
    assert r.status_code == 401


def test_mobile_positions_with_valid_token(client_with_token):
    client, token = client_with_token
    r = client.get("/api/v1/mobile/positions", headers={"X-Api-Key": token})
    assert r.status_code == 200
    body = r.json()
    assert "positions" in body


def test_manifest_endpoint(client_with_token):
    client, _ = client_with_token
    r = client.get("/manifest.json")
    # 200 if manifest.json exists, 404 otherwise -- both acceptable
    assert r.status_code in (200, 404)


def test_sw_endpoint(client_with_token):
    client, _ = client_with_token
    r = client.get("/sw.js")
    # 200 if sw.js exists, 404 otherwise -- both acceptable
    assert r.status_code in (200, 404)


def test_wrong_api_key_rejected(client_with_token):
    client, token = client_with_token
    r = client.get("/api/v1/mobile/dashboard", headers={"X-Api-Key": "wrong-key"})
    assert r.status_code == 401
    assert r.json()["error"] == "invalid_api_key"
