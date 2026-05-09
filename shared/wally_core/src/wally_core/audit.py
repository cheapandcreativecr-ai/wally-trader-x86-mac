"""Cryptographically chained audit log."""
from __future__ import annotations
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _audit_log_path() -> Path:
    base = Path(os.environ.get("WALLY_PROFILES_DIR", ".claude/profiles"))
    p = base / "_audit" / "audit.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _hash_entry(prev_hash: str, payload: dict) -> str:
    """Compute sha256(prev_hash || canonical_json(payload))."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    h = hashlib.sha256()
    h.update(prev_hash.encode())
    h.update(canonical.encode())
    return h.hexdigest()


def append(event: str, payload: dict, *, audit_path: Optional[Path] = None) -> str:
    """Append event to chain. Returns the new entry's hash."""
    audit_path = audit_path or _audit_log_path()

    # Read last hash
    prev_hash = "0" * 64
    if audit_path.exists():
        last_line = ""
        with open(audit_path) as f:
            for line in f:
                last_line = line
        if last_line.strip():
            last = json.loads(last_line)
            prev_hash = last.get("hash", prev_hash)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "payload": payload,
        "prev_hash": prev_hash,
    }
    entry["hash"] = _hash_entry(prev_hash, {"timestamp": entry["timestamp"], "event": event, "payload": payload})

    with open(audit_path, "a") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())

    return entry["hash"]


def verify_chain(audit_path: Optional[Path] = None) -> dict:
    """Verify entire chain integrity. Returns {ok, n_entries, broken_at}."""
    audit_path = audit_path or _audit_log_path()
    if not audit_path.exists():
        return {"ok": True, "n_entries": 0, "reason": "no_log"}

    prev_hash = "0" * 64
    n = 0

    with open(audit_path) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                return {"ok": False, "n_entries": n, "broken_at": line_num, "reason": "invalid_json"}

            if entry.get("prev_hash") != prev_hash:
                return {"ok": False, "n_entries": n, "broken_at": line_num, "reason": "prev_hash_mismatch"}

            expected = _hash_entry(prev_hash, {
                "timestamp": entry["timestamp"],
                "event": entry["event"],
                "payload": entry["payload"],
            })
            if entry.get("hash") != expected:
                return {"ok": False, "n_entries": n, "broken_at": line_num, "reason": "hash_mismatch"}

            prev_hash = entry["hash"]
            n += 1

    return {"ok": True, "n_entries": n, "last_hash": prev_hash}
