import json
import pytest
from pathlib import Path
from wally_core.audit import append, verify_chain


def test_append_creates_log(tmp_path):
    log = tmp_path / "audit.jsonl"
    h1 = append("test_event", {"data": "hello"}, audit_path=log)
    assert log.exists()
    assert len(h1) == 64


def test_chain_verifies_after_appends(tmp_path):
    log = tmp_path / "audit.jsonl"
    append("event1", {"a": 1}, audit_path=log)
    append("event2", {"b": 2}, audit_path=log)
    append("event3", {"c": 3}, audit_path=log)

    result = verify_chain(audit_path=log)
    assert result["ok"]
    assert result["n_entries"] == 3


def test_chain_detects_tampering(tmp_path):
    log = tmp_path / "audit.jsonl"
    append("event1", {"a": 1}, audit_path=log)
    append("event2", {"b": 2}, audit_path=log)

    # Tamper with second entry
    lines = log.read_text().splitlines()
    e = json.loads(lines[1])
    e["payload"]["b"] = 999  # corruption
    lines[1] = json.dumps(e, sort_keys=True)
    log.write_text("\n".join(lines) + "\n")

    result = verify_chain(audit_path=log)
    assert not result["ok"]
    assert "broken_at" in result


def test_empty_chain_is_ok(tmp_path):
    log = tmp_path / "audit.jsonl"
    result = verify_chain(audit_path=log)
    assert result["ok"]
    assert result["n_entries"] == 0


def test_single_entry_hash_structure(tmp_path):
    log = tmp_path / "audit.jsonl"
    h = append("smoke", {"k": "v"}, audit_path=log)
    lines = log.read_text().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["hash"] == h
    assert entry["prev_hash"] == "0" * 64
    assert entry["event"] == "smoke"


def test_prev_hash_chaining(tmp_path):
    log = tmp_path / "audit.jsonl"
    h1 = append("e1", {"x": 1}, audit_path=log)
    append("e2", {"x": 2}, audit_path=log)
    lines = log.read_text().splitlines()
    e2 = json.loads(lines[1])
    assert e2["prev_hash"] == h1
