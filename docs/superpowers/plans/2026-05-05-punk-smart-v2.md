# /punk-smart v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `/punk-smart` to a 5-stage pipeline (kill-switch → per-asset mapping → strategy → 6-veto layer → dynamic sizing → trail-SL annotation) that targets WR ≥55% and max-DD ≤15% by being more selective and applying confidence-weighted sizing.

**Architecture:** Add four new modules under `.claude/scripts/` (`punk_smart_state.py`, `punk_smart_vetos.py`, `regime_confidence.py`, refactored `punk_smart_router.py`) plus per-profile state JSON files. Schema v2 of `regime_mapping.json` adds per-asset overrides + flags for granular rollback. Backtest extended to 60 days with paginated Binance fetch.

**Tech Stack:** Python 3 stdlib only (urllib, json, csv, datetime), pytest 9 for unit tests, launchd for daily reset, shell for CLI integration. Reuses existing helpers: `macro_gate.py`, `bitunix_log.py`, `backtest_split.py`.

**Spec:** [`docs/superpowers/specs/2026-05-05-punk-smart-v2-design.md`](../specs/2026-05-05-punk-smart-v2-design.md)

---

## File Structure

Maps spec components to files. Each file has one responsibility.

```
.claude/scripts/
├── punk_smart_state.py           [NEW]    Read/write state JSONs (blacklist, sl_window, open positions)
├── punk_smart_vetos.py           [NEW]    6 veto functions (pure: setup → {passed, reason})
├── regime_confidence.py          [NEW]    Sizing formula: pnl_per_trade → size_mult
├── punk_smart_router.py          [MOD]    5-stage pipeline orchestrator
├── backtest_regime_matrix.py     [MOD]    Add fetch_paginated, cells_per_asset, trail SL in simulate
├── regime_mapping.json           [SCHEMA] v2 with per-asset + flags
├── regime_mapping.v1.backup      [NEW]    Frozen copy of v1 for rollback
└── bitunix_log.py                [MOD]    Hook on outcome: notify state machine

.claude/profiles/bitunix/memory/
├── asset_sl_streaks.json         [NEW]    Per-asset SL count + blacklist_until
└── sl_window.json                [NEW]    Recent SL events + kill_switch_active_until

.claude/launchd/
└── com.wally.bitunix-daily-reset.plist  [NEW]   Reset state files at CR 00:00

tests/punk_smart/
├── __init__.py
├── conftest.py                   [NEW]    Fixtures: tmp profile dir, frozen time
├── test_state.py                 [NEW]    State machine logic
├── test_vetos.py                 [NEW]    Each veto independently
├── test_regime_confidence.py     [NEW]    Sizing clip math
└── test_backtest_paginated.py    [NEW]    Paginated fetch contract

docs/
└── backtest_findings_2026-05-05_punk_smart_v2.md  [NEW]   Generated post-backtest
```

**Key boundary decisions:**
- State module knows about file paths but exposes pure functions (`is_blacklisted(asset, now)`, `record_sl(asset, ts, pnl)`).
- Veto module imports state but vetos themselves are pure: `(setup, side, asset, ctx) → VetoResult`.
- Router is the only orchestrator that knows about all stages.
- Tests use a tmp profile dir + injected `now` to avoid clock/state leakage between tests.

---

## Task 0: Branch + scaffolding

**Files:**
- Create: `tests/punk_smart/__init__.py`
- Create: `tests/punk_smart/conftest.py`
- Create branch: `feat/punk-smart-v2`

- [ ] **Step 1: Create the branch**

```bash
git checkout -b feat/punk-smart-v2
```

- [ ] **Step 2: Verify pytest works**

```bash
pytest --version
```

Expected: `pytest 9.0.3` (or compatible).

- [ ] **Step 3: Create test scaffolding**

```bash
mkdir -p tests/punk_smart
```

Create `tests/punk_smart/__init__.py` as an empty file.

Create `tests/punk_smart/conftest.py`:

```python
"""Shared fixtures for punk_smart tests."""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

CR_OFFSET = timezone(timedelta(hours=-6))


@pytest.fixture
def tmp_profile_dir(tmp_path, monkeypatch):
    """Provide an isolated profile dir that mimics bitunix layout."""
    profile = tmp_path / "profiles" / "bitunix" / "memory"
    profile.mkdir(parents=True)
    monkeypatch.setenv("WALLY_PROFILE", "bitunix")
    monkeypatch.setenv("WALLY_PROFILE_MEMORY_DIR", str(profile))
    return profile


@pytest.fixture
def cr_time():
    """Build a CR-zoned datetime."""
    def _make(year, month, day, hour=0, minute=0):
        return datetime(year, month, day, hour, minute, tzinfo=CR_OFFSET)
    return _make


@pytest.fixture
def signals_csv_factory(tmp_profile_dir):
    """Write a signals_received.csv with arbitrary rows."""
    csv_path = tmp_profile_dir / "signals_received.csv"
    HEADER = ("date,time,symbol,side,entry,sl,tp,leverage_signal,day_of_week,"
              "filters_4,multifactor,ml_score,chainlink_delta,regime,"
              "pillars_4_count,saturday,verdict,decision,size_pct,executed,"
              "exit_price,exit_reason,pnl_usd,duration_h,hypothetical_outcome,"
              "learning,tier")

    def _write(rows):
        lines = [HEADER]
        for r in rows:
            lines.append(",".join(str(r.get(k, "")) for k in HEADER.split(",")))
        csv_path.write_text("\n".join(lines) + "\n")
        return csv_path
    return _write
```

- [ ] **Step 4: Verify scaffolding loads**

```bash
pytest tests/punk_smart/ -v --collect-only
```

Expected: `no tests ran` but no import errors.

- [ ] **Step 5: Commit**

```bash
git add tests/punk_smart/__init__.py tests/punk_smart/conftest.py
git commit -m "test(punk-smart-v2): scaffold tests dir + conftest fixtures"
```

---

## Task 1: State — asset SL streak tracker

**Files:**
- Create: `.claude/scripts/punk_smart_state.py`
- Test: `tests/punk_smart/test_state.py`

- [ ] **Step 1: Write the failing test**

Create `tests/punk_smart/test_state.py`:

```python
"""Tests for punk_smart_state module."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".claude" / "scripts"))

import punk_smart_state as state


class TestAssetBlacklist:
    def test_blacklist_after_2sl_same_day(self, tmp_profile_dir, cr_time):
        state.record_sl("XLMUSDT", cr_time(2026, 5, 5, 9, 14), pnl_usd=-3.20,
                        memory_dir=tmp_profile_dir)
        assert not state.is_blacklisted("XLMUSDT", cr_time(2026, 5, 5, 10, 0),
                                         memory_dir=tmp_profile_dir)
        state.record_sl("XLMUSDT", cr_time(2026, 5, 5, 11, 23), pnl_usd=-4.05,
                        memory_dir=tmp_profile_dir)
        assert state.is_blacklisted("XLMUSDT", cr_time(2026, 5, 5, 12, 0),
                                     memory_dir=tmp_profile_dir)

    def test_blacklist_clears_on_tp(self, tmp_profile_dir, cr_time):
        state.record_sl("XLMUSDT", cr_time(2026, 5, 5, 9, 0), pnl_usd=-3.20,
                        memory_dir=tmp_profile_dir)
        state.record_tp("XLMUSDT", cr_time(2026, 5, 5, 10, 0),
                        memory_dir=tmp_profile_dir)
        # Now next SL should not blacklist (count was reset)
        state.record_sl("XLMUSDT", cr_time(2026, 5, 5, 11, 0), pnl_usd=-3.20,
                        memory_dir=tmp_profile_dir)
        assert not state.is_blacklisted("XLMUSDT", cr_time(2026, 5, 5, 12, 0),
                                         memory_dir=tmp_profile_dir)

    def test_blacklist_expires_next_cr_midnight(self, tmp_profile_dir, cr_time):
        state.record_sl("XLMUSDT", cr_time(2026, 5, 5, 22, 0), pnl_usd=-3.20,
                        memory_dir=tmp_profile_dir)
        state.record_sl("XLMUSDT", cr_time(2026, 5, 5, 23, 0), pnl_usd=-3.20,
                        memory_dir=tmp_profile_dir)
        assert state.is_blacklisted("XLMUSDT", cr_time(2026, 5, 5, 23, 30),
                                     memory_dir=tmp_profile_dir)
        # After CR 00:00 next day → expired
        assert not state.is_blacklisted("XLMUSDT", cr_time(2026, 5, 6, 0, 1),
                                         memory_dir=tmp_profile_dir)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/punk_smart/test_state.py -v
```

Expected: FAIL with `ModuleNotFoundError: punk_smart_state`.

- [ ] **Step 3: Write minimal implementation**

Create `.claude/scripts/punk_smart_state.py`:

```python
#!/usr/bin/env python3
"""punk_smart_state — file-backed state for /punk-smart v2.

Three state files inside the active profile's memory dir:
  asset_sl_streaks.json — per-asset SL count + blacklist_until
  sl_window.json        — recent SL events + kill_switch_active_until
  signals_received.csv  — read-only, used to derive open positions

Public API:
  record_sl(asset, ts, pnl_usd, memory_dir=None)
  record_tp(asset, ts, memory_dir=None)
  is_blacklisted(asset, now, memory_dir=None) -> bool
  is_kill_switch_active(now, memory_dir=None) -> (bool, str|None)
  open_positions(memory_dir=None) -> [{asset, side, bucket}]
  reset_killswitch(memory_dir=None)
"""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

CR_OFFSET = timezone(timedelta(hours=-6))


def _memory_dir(memory_dir: Path | None = None) -> Path:
    if memory_dir is not None:
        return Path(memory_dir)
    env = os.environ.get("WALLY_PROFILE_MEMORY_DIR")
    if env:
        return Path(env)
    profile = os.environ.get("WALLY_PROFILE", "bitunix")
    return Path(__file__).resolve().parents[1] / "profiles" / profile / "memory"


def _load(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return default


def _save(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str))


def _next_cr_midnight(ts: datetime) -> datetime:
    cr_ts = ts.astimezone(CR_OFFSET)
    midnight = cr_ts.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return midnight


def _streaks_path(memory_dir: Path | None) -> Path:
    return _memory_dir(memory_dir) / "asset_sl_streaks.json"


def record_sl(asset: str, ts: datetime, pnl_usd: float,
              memory_dir: Path | None = None) -> None:
    p = _streaks_path(memory_dir)
    data = _load(p, {"version": 1, "as_of_cr_date": None, "assets": {}})
    cell = data["assets"].get(asset, {"sl_count": 0, "last_sl_ts": None,
                                       "blacklist_until": None})
    cell["sl_count"] = cell.get("sl_count", 0) + 1
    cell["last_sl_ts"] = ts.isoformat()
    if cell["sl_count"] >= 2:
        cell["blacklist_until"] = _next_cr_midnight(ts).isoformat()
    data["assets"][asset] = cell
    data["as_of_cr_date"] = ts.astimezone(CR_OFFSET).date().isoformat()
    _save(p, data)


def record_tp(asset: str, ts: datetime, memory_dir: Path | None = None) -> None:
    p = _streaks_path(memory_dir)
    data = _load(p, {"version": 1, "as_of_cr_date": None, "assets": {}})
    if asset in data["assets"]:
        data["assets"][asset]["sl_count"] = 0
        data["assets"][asset]["blacklist_until"] = None
        data["as_of_cr_date"] = ts.astimezone(CR_OFFSET).date().isoformat()
        _save(p, data)


def is_blacklisted(asset: str, now: datetime,
                   memory_dir: Path | None = None) -> bool:
    p = _streaks_path(memory_dir)
    data = _load(p, {"assets": {}})
    cell = data.get("assets", {}).get(asset)
    if not cell or not cell.get("blacklist_until"):
        return False
    return now < datetime.fromisoformat(cell["blacklist_until"])
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/punk_smart/test_state.py::TestAssetBlacklist -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/punk_smart_state.py tests/punk_smart/test_state.py
git commit -m "feat(punk-smart-v2): asset SL streak tracker + blacklist"
```

---

## Task 2: State — kill-switch (2 SLs in 4h window)

**Files:**
- Modify: `.claude/scripts/punk_smart_state.py`
- Modify: `tests/punk_smart/test_state.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/punk_smart/test_state.py`:

```python
class TestKillSwitch:
    def test_2sl_in_4h_activates_killswitch(self, tmp_profile_dir, cr_time):
        state.record_sl("ETHUSDT", cr_time(2026, 5, 5, 10, 15), pnl_usd=-3.85,
                        memory_dir=tmp_profile_dir)
        active, _ = state.is_kill_switch_active(cr_time(2026, 5, 5, 11, 0),
                                                 memory_dir=tmp_profile_dir)
        assert not active
        state.record_sl("AVAXUSDT", cr_time(2026, 5, 5, 11, 50), pnl_usd=-4.10,
                        memory_dir=tmp_profile_dir)
        active, reason = state.is_kill_switch_active(cr_time(2026, 5, 5, 12, 0),
                                                      memory_dir=tmp_profile_dir)
        assert active
        assert "2 SL" in reason or "kill" in reason.lower()

    def test_killswitch_purge_old_events(self, tmp_profile_dir, cr_time):
        state.record_sl("BTCUSDT", cr_time(2026, 5, 5, 6, 0), pnl_usd=-3.0,
                        memory_dir=tmp_profile_dir)
        # 5h later — first SL is outside the 4h window now
        state.record_sl("ETHUSDT", cr_time(2026, 5, 5, 11, 0), pnl_usd=-3.0,
                        memory_dir=tmp_profile_dir)
        active, _ = state.is_kill_switch_active(cr_time(2026, 5, 5, 11, 30),
                                                 memory_dir=tmp_profile_dir)
        assert not active

    def test_killswitch_persists_until_cr_midnight(self, tmp_profile_dir, cr_time):
        state.record_sl("BTCUSDT", cr_time(2026, 5, 5, 22, 0), pnl_usd=-3.0,
                        memory_dir=tmp_profile_dir)
        state.record_sl("ETHUSDT", cr_time(2026, 5, 5, 23, 30), pnl_usd=-3.0,
                        memory_dir=tmp_profile_dir)
        active, _ = state.is_kill_switch_active(cr_time(2026, 5, 5, 23, 45),
                                                 memory_dir=tmp_profile_dir)
        assert active
        active, _ = state.is_kill_switch_active(cr_time(2026, 5, 6, 0, 1),
                                                 memory_dir=tmp_profile_dir)
        assert not active

    def test_reset_killswitch(self, tmp_profile_dir, cr_time):
        state.record_sl("BTCUSDT", cr_time(2026, 5, 5, 10, 0), pnl_usd=-3.0,
                        memory_dir=tmp_profile_dir)
        state.record_sl("ETHUSDT", cr_time(2026, 5, 5, 11, 0), pnl_usd=-3.0,
                        memory_dir=tmp_profile_dir)
        state.reset_killswitch(memory_dir=tmp_profile_dir)
        active, _ = state.is_kill_switch_active(cr_time(2026, 5, 5, 12, 0),
                                                 memory_dir=tmp_profile_dir)
        assert not active
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/punk_smart/test_state.py::TestKillSwitch -v
```

Expected: 4 tests FAIL with `AttributeError: ... is_kill_switch_active`.

- [ ] **Step 3: Write minimal implementation**

Append to `.claude/scripts/punk_smart_state.py`:

```python
def _window_path(memory_dir: Path | None) -> Path:
    return _memory_dir(memory_dir) / "sl_window.json"


def _purge_old_events(events: list[dict], now: datetime, hours: int = 4) -> list[dict]:
    cutoff = now - timedelta(hours=hours)
    fresh = []
    for ev in events:
        ts = datetime.fromisoformat(ev["ts"])
        if ts >= cutoff:
            fresh.append(ev)
    return fresh


def _record_sl_window(asset: str, ts: datetime, pnl_usd: float,
                      memory_dir: Path | None = None) -> None:
    p = _window_path(memory_dir)
    data = _load(p, {"events": [], "kill_switch_active_until": None})
    data["events"].append({"ts": ts.isoformat(), "asset": asset,
                            "pnl_usd": pnl_usd})
    data["events"] = _purge_old_events(data["events"], ts, hours=4)
    if len(data["events"]) >= 2:
        data["kill_switch_active_until"] = _next_cr_midnight(ts).isoformat()
    _save(p, data)


def is_kill_switch_active(now: datetime,
                          memory_dir: Path | None = None) -> tuple[bool, str | None]:
    p = _window_path(memory_dir)
    data = _load(p, {"events": [], "kill_switch_active_until": None})
    until = data.get("kill_switch_active_until")
    if not until:
        return False, None
    until_dt = datetime.fromisoformat(until)
    if now >= until_dt:
        return False, None
    return True, f"PAUSED: 2 SL kill-switch active until {until_dt.isoformat()}"


def reset_killswitch(memory_dir: Path | None = None) -> None:
    p = _window_path(memory_dir)
    data = _load(p, {"events": [], "kill_switch_active_until": None})
    data["kill_switch_active_until"] = None
    data["events"] = []
    _save(p, data)
```

Modify `record_sl` (still in same file) to also call `_record_sl_window`:

```python
def record_sl(asset: str, ts: datetime, pnl_usd: float,
              memory_dir: Path | None = None) -> None:
    # ... existing body ...
    _save(p, data)
    _record_sl_window(asset, ts, pnl_usd, memory_dir)
```

- [ ] **Step 4: Run all state tests**

```bash
pytest tests/punk_smart/test_state.py -v
```

Expected: 7 tests PASS (3 previous + 4 new).

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/punk_smart_state.py tests/punk_smart/test_state.py
git commit -m "feat(punk-smart-v2): kill-switch (2 SLs in 4h window)"
```

---

## Task 3: State — open positions reader

**Files:**
- Modify: `.claude/scripts/punk_smart_state.py`
- Modify: `tests/punk_smart/test_state.py`

Reads `signals_received.csv` and returns rows with no `exit_price` (i.e. open). Adds bucket lookup.

- [ ] **Step 1: Write the failing test**

Append to `tests/punk_smart/test_state.py`:

```python
class TestOpenPositions:
    def test_no_csv_returns_empty(self, tmp_profile_dir):
        result = state.open_positions(memory_dir=tmp_profile_dir)
        assert result == []

    def test_reads_open_rows(self, tmp_profile_dir, signals_csv_factory):
        signals_csv_factory([
            {"symbol": "BTCUSDT.P", "side": "LONG", "exit_price": ""},
            {"symbol": "ETHUSDT.P", "side": "SHORT", "exit_price": "2370.00"},  # closed
            {"symbol": "SOLUSDT.P", "side": "LONG", "exit_price": ""},
        ])
        result = state.open_positions(memory_dir=tmp_profile_dir)
        assert len(result) == 2
        assert {(r["asset"], r["side"]) for r in result} == \
               {("BTCUSDT", "LONG"), ("SOLUSDT", "LONG")}

    def test_attaches_bucket(self, tmp_profile_dir, signals_csv_factory):
        signals_csv_factory([
            {"symbol": "BTCUSDT.P", "side": "LONG", "exit_price": ""},
            {"symbol": "DOGEUSDT.P", "side": "SHORT", "exit_price": ""},
        ])
        result = state.open_positions(memory_dir=tmp_profile_dir)
        buckets = {r["asset"]: r["bucket"] for r in result}
        assert buckets["BTCUSDT"] == "btc_majors"
        assert buckets["DOGEUSDT"] == "memes"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/punk_smart/test_state.py::TestOpenPositions -v
```

Expected: 3 tests FAIL with `AttributeError: open_positions`.

- [ ] **Step 3: Write minimal implementation**

Append to `.claude/scripts/punk_smart_state.py`:

```python
BUCKETS = {
    "btc_majors":  ["BTCUSDT", "ETHUSDT", "SOLUSDT", "MSTRUSDT"],
    "l1_alts":     ["AVAXUSDT", "INJUSDT", "ADAUSDT", "TRXUSDT", "LINKUSDT",
                    "SUIUSDT", "TONUSDT", "HBARUSDT"],
    "memes":       ["DOGEUSDT", "WIFUSDT", "FARTCOINUSDT", "PEPEUSDT"],
    "small_caps":  ["XLMUSDT", "ENJUSDT", "CHZUSDT", "AXSUSDT", "SEIUSDT",
                    "POLUSDT", "TIAUSDT", "ROSEUSDT", "RUNEUSDT"],
}


def bucket_of(asset: str) -> str | None:
    norm = asset.replace(".P", "").upper()
    for name, members in BUCKETS.items():
        if norm in members:
            return name
    return None


def open_positions(memory_dir: Path | None = None) -> list[dict]:
    p = _memory_dir(memory_dir) / "signals_received.csv"
    if not p.exists():
        return []
    with p.open() as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        if r.get("exit_price"):
            continue
        sym = r.get("symbol", "").replace(".P", "").upper()
        if not sym:
            continue
        out.append({
            "asset": sym,
            "side": r.get("side", "").upper(),
            "bucket": bucket_of(sym),
        })
    return out
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/punk_smart/test_state.py -v
```

Expected: 10 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/punk_smart_state.py tests/punk_smart/test_state.py
git commit -m "feat(punk-smart-v2): open-positions reader + bucket lookup"
```

---

## Task 4: Veto — macro events

**Files:**
- Create: `.claude/scripts/punk_smart_vetos.py`
- Test: `tests/punk_smart/test_vetos.py`

- [ ] **Step 1: Write the failing test**

Create `tests/punk_smart/test_vetos.py`:

```python
"""Tests for punk_smart_vetos."""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".claude" / "scripts"))

import punk_smart_vetos as vetos


class TestMacroVeto:
    def test_clear_when_no_event(self, monkeypatch):
        monkeypatch.setattr(vetos, "_macro_check",
                            lambda: {"blocked": False, "reason": None})
        result = vetos.veto_macro({"side": "LONG"})
        assert result.passed is True
        assert "clear" in result.reason.lower()

    def test_blocked_when_event_within_30min(self, monkeypatch):
        monkeypatch.setattr(vetos, "_macro_check",
                            lambda: {"blocked": True, "reason": "FOMC in 22 min"})
        result = vetos.veto_macro({"side": "LONG"})
        assert result.passed is False
        assert "FOMC" in result.reason
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/punk_smart/test_vetos.py::TestMacroVeto -v
```

Expected: FAIL with `ModuleNotFoundError: punk_smart_vetos`.

- [ ] **Step 3: Write minimal implementation**

Create `.claude/scripts/punk_smart_vetos.py`:

```python
#!/usr/bin/env python3
"""punk_smart_vetos — 6 veto functions for /punk-smart v2.

Each veto: (setup, ctx) → VetoResult(passed: bool, reason: str, source: str).
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent


@dataclass
class VetoResult:
    name: str
    passed: bool
    reason: str
    source: str = ""


def _macro_check() -> dict:
    """Run macro_gate.py --check-now and return parsed JSON.

    Indirected via a function so tests can monkeypatch.
    """
    venv_py = SCRIPTS_DIR / ".venv" / "bin" / "python"
    py = str(venv_py) if venv_py.exists() else sys.executable
    try:
        out = subprocess.check_output(
            [py, str(SCRIPTS_DIR / "macro_gate.py"), "--check-now"],
            timeout=10, stderr=subprocess.DEVNULL)
        return json.loads(out)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
            json.JSONDecodeError):
        return {"blocked": False, "reason": None}


def veto_macro(setup: dict) -> VetoResult:
    chk = _macro_check()
    if chk.get("blocked"):
        return VetoResult("macro", False, chk.get("reason", "macro event"),
                          source="macro_gate")
    return VetoResult("macro", True, "clear", source="macro_gate")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/punk_smart/test_vetos.py::TestMacroVeto -v
```

Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/punk_smart_vetos.py tests/punk_smart/test_vetos.py
git commit -m "feat(punk-smart-v2): veto #1 macro events"
```

---

## Task 5: Veto — asset blacklist + concurrent correlation

**Files:**
- Modify: `.claude/scripts/punk_smart_vetos.py`
- Modify: `tests/punk_smart/test_vetos.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/punk_smart/test_vetos.py`:

```python
class TestBlacklistVeto:
    def test_clear_when_not_blacklisted(self, tmp_profile_dir, cr_time):
        result = vetos.veto_blacklist({"asset": "ETHUSDT"},
                                       now=cr_time(2026, 5, 5, 10, 0),
                                       memory_dir=tmp_profile_dir)
        assert result.passed is True

    def test_blocked_when_2sl_streak(self, tmp_profile_dir, cr_time):
        import punk_smart_state as state
        state.record_sl("XLMUSDT", cr_time(2026, 5, 5, 9, 0), pnl_usd=-3.0,
                        memory_dir=tmp_profile_dir)
        state.record_sl("XLMUSDT", cr_time(2026, 5, 5, 10, 0), pnl_usd=-3.0,
                        memory_dir=tmp_profile_dir)
        result = vetos.veto_blacklist({"asset": "XLMUSDT"},
                                       now=cr_time(2026, 5, 5, 11, 0),
                                       memory_dir=tmp_profile_dir)
        assert result.passed is False
        assert "blacklist" in result.reason.lower() or "2 sl" in result.reason.lower()


class TestCorrelationVeto:
    def test_clear_when_no_open_in_bucket(self, tmp_profile_dir, signals_csv_factory):
        signals_csv_factory([])  # no open positions
        result = vetos.veto_correlation({"asset": "BTCUSDT", "side": "LONG"},
                                         memory_dir=tmp_profile_dir)
        assert result.passed is True

    def test_blocked_when_same_bucket_same_side_open(self, tmp_profile_dir,
                                                      signals_csv_factory):
        signals_csv_factory([
            {"symbol": "BTCUSDT.P", "side": "LONG", "exit_price": ""},
        ])
        result = vetos.veto_correlation({"asset": "ETHUSDT", "side": "LONG"},
                                         memory_dir=tmp_profile_dir)
        assert result.passed is False
        assert "btc_majors" in result.reason.lower()

    def test_clear_when_opposite_side_open(self, tmp_profile_dir, signals_csv_factory):
        signals_csv_factory([
            {"symbol": "BTCUSDT.P", "side": "LONG", "exit_price": ""},
        ])
        result = vetos.veto_correlation({"asset": "ETHUSDT", "side": "SHORT"},
                                         memory_dir=tmp_profile_dir)
        assert result.passed is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/punk_smart/test_vetos.py -v -k "Blacklist or Correlation"
```

Expected: 5 tests FAIL with `AttributeError: veto_blacklist / veto_correlation`.

- [ ] **Step 3: Write minimal implementation**

Append to `.claude/scripts/punk_smart_vetos.py`:

```python
import punk_smart_state as state


def veto_blacklist(setup: dict, now, memory_dir=None) -> VetoResult:
    asset = setup["asset"]
    if state.is_blacklisted(asset, now, memory_dir=memory_dir):
        return VetoResult("blacklist", False,
                          f"{asset} blacklisted (2 SL streak)",
                          source="asset_sl_streaks.json")
    return VetoResult("blacklist", True, "clean", source="asset_sl_streaks.json")


def veto_correlation(setup: dict, memory_dir=None) -> VetoResult:
    asset = setup["asset"]
    side = setup["side"].upper()
    bucket = state.bucket_of(asset)
    if bucket is None:
        return VetoResult("correlation", True,
                          f"{asset} unbucketed — no correlation check",
                          source="signals_received.csv")
    open_pos = state.open_positions(memory_dir=memory_dir)
    for p in open_pos:
        if p["bucket"] == bucket and p["side"] == side and p["asset"] != asset:
            return VetoResult(
                "correlation", False,
                f"{p['asset']} {side} already open in {bucket} bucket",
                source="signals_received.csv")
    return VetoResult("correlation", True, "no conflict",
                      source="signals_received.csv")
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/punk_smart/test_vetos.py -v
```

Expected: 7 tests PASS (2 macro + 2 blacklist + 3 correlation).

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/punk_smart_vetos.py tests/punk_smart/test_vetos.py
git commit -m "feat(punk-smart-v2): vetos #2 blacklist + #3 correlation"
```

---

## Task 6: Veto — sentiment + funding contrarian

**Files:**
- Modify: `.claude/scripts/punk_smart_vetos.py`
- Modify: `tests/punk_smart/test_vetos.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/punk_smart/test_vetos.py`:

```python
class TestSentimentVeto:
    def test_clear_when_neutral(self, monkeypatch):
        monkeypatch.setattr(vetos, "_fng_now", lambda: 50)
        assert vetos.veto_sentiment({"side": "LONG"}).passed
        assert vetos.veto_sentiment({"side": "SHORT"}).passed

    def test_blocks_long_when_extreme_greed(self, monkeypatch):
        monkeypatch.setattr(vetos, "_fng_now", lambda: 85)
        result = vetos.veto_sentiment({"side": "LONG"})
        assert result.passed is False
        assert "85" in result.reason or "greed" in result.reason.lower()

    def test_blocks_short_when_extreme_fear(self, monkeypatch):
        monkeypatch.setattr(vetos, "_fng_now", lambda: 15)
        assert vetos.veto_sentiment({"side": "SHORT"}).passed is False

    def test_allows_long_in_fear(self, monkeypatch):
        monkeypatch.setattr(vetos, "_fng_now", lambda: 15)
        assert vetos.veto_sentiment({"side": "LONG"}).passed


class TestFundingVeto:
    def test_clear_when_funding_neutral(self, monkeypatch):
        monkeypatch.setattr(vetos, "_funding_now", lambda asset: 0.0001)
        assert vetos.veto_funding({"asset": "BTCUSDT", "side": "LONG"}).passed

    def test_blocks_long_when_funding_extreme_positive(self, monkeypatch):
        monkeypatch.setattr(vetos, "_funding_now", lambda asset: 0.0006)
        result = vetos.veto_funding({"asset": "BTCUSDT", "side": "LONG"})
        assert result.passed is False
        assert "funding" in result.reason.lower()

    def test_blocks_short_when_funding_extreme_negative(self, monkeypatch):
        monkeypatch.setattr(vetos, "_funding_now", lambda asset: -0.0006)
        assert not vetos.veto_funding({"asset": "BTCUSDT", "side": "SHORT"}).passed
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/punk_smart/test_vetos.py -v -k "Sentiment or Funding"
```

Expected: 7 FAIL with `AttributeError`.

- [ ] **Step 3: Write minimal implementation**

Append to `.claude/scripts/punk_smart_vetos.py`:

```python
import time
import urllib.request

_FNG_CACHE = {"value": None, "fetched_at": 0}
_FUNDING_CACHE: dict = {}  # asset → {value, fetched_at}


def _fng_now() -> int | None:
    """Return current Fear & Greed value (0-100). Cache 1h."""
    if time.time() - _FNG_CACHE["fetched_at"] < 3600 and _FNG_CACHE["value"] is not None:
        return _FNG_CACHE["value"]
    try:
        with urllib.request.urlopen("https://api.alternative.me/fng/?limit=1",
                                     timeout=5) as resp:
            data = json.loads(resp.read())
        v = int(data["data"][0]["value"])
        _FNG_CACHE.update({"value": v, "fetched_at": time.time()})
        return v
    except Exception:
        return None


def _funding_now(asset: str) -> float | None:
    """Return current 8h-funding-rate for asset. Cache 30 min."""
    okx_id = asset.replace("USDT", "-USDT-SWAP")
    cache = _FUNDING_CACHE.get(asset)
    if cache and time.time() - cache["fetched_at"] < 1800:
        return cache["value"]
    try:
        url = f"https://www.okx.com/api/v5/public/funding-rate?instId={okx_id}"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
        if data.get("code") != "0" or not data.get("data"):
            return None
        v = float(data["data"][0]["fundingRate"])
        _FUNDING_CACHE[asset] = {"value": v, "fetched_at": time.time()}
        return v
    except Exception:
        return None


def veto_sentiment(setup: dict) -> VetoResult:
    fng = _fng_now()
    if fng is None:
        return VetoResult("sentiment", True, "F&G unavailable — skipped",
                          source="alternative.me/fng")
    side = setup["side"].upper()
    if side == "LONG" and fng >= 80:
        return VetoResult("sentiment", False,
                          f"F&G {fng} (extreme greed) vs LONG — contrarian veto",
                          source="alternative.me/fng")
    if side == "SHORT" and fng <= 20:
        return VetoResult("sentiment", False,
                          f"F&G {fng} (extreme fear) vs SHORT — contrarian veto",
                          source="alternative.me/fng")
    return VetoResult("sentiment", True, f"F&G {fng} OK",
                      source="alternative.me/fng")


def veto_funding(setup: dict) -> VetoResult:
    fr = _funding_now(setup["asset"])
    if fr is None:
        return VetoResult("funding", True, "funding unavailable — skipped",
                          source="okx funding-rate")
    side = setup["side"].upper()
    if side == "LONG" and fr >= 0.0005:
        return VetoResult("funding", False,
                          f"funding {fr*100:.4f}% vs LONG — too crowded long",
                          source="okx funding-rate")
    if side == "SHORT" and fr <= -0.0005:
        return VetoResult("funding", False,
                          f"funding {fr*100:.4f}% vs SHORT — too crowded short",
                          source="okx funding-rate")
    return VetoResult("funding", True, f"funding {fr*100:.4f}% OK",
                      source="okx funding-rate")
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/punk_smart/test_vetos.py -v
```

Expected: 14 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/punk_smart_vetos.py tests/punk_smart/test_vetos.py
git commit -m "feat(punk-smart-v2): vetos #4 sentiment + #5 funding (contrarian)"
```

---

## Task 7: Veto — time-of-day weak window (soft)

**Files:**
- Modify: `.claude/scripts/punk_smart_vetos.py`
- Modify: `tests/punk_smart/test_vetos.py`

Soft veto: blocks only if regime quality is below threshold.

- [ ] **Step 1: Write the failing test**

Append to `tests/punk_smart/test_vetos.py`:

```python
class TestTimeOfDayVeto:
    def test_clear_during_active_window(self, cr_time):
        result = vetos.veto_time_of_day({"side": "LONG"}, regime_pnl_per_trade=2.5,
                                          now=cr_time(2026, 5, 5, 10, 0))
        assert result.passed is True

    def test_blocks_during_weak_window_low_quality_regime(self, cr_time):
        result = vetos.veto_time_of_day({"side": "LONG"}, regime_pnl_per_trade=0.5,
                                          now=cr_time(2026, 5, 5, 23, 0))
        assert result.passed is False
        assert "weak window" in result.reason.lower() or "asian" in result.reason.lower()

    def test_overrides_when_regime_high_quality(self, cr_time):
        result = vetos.veto_time_of_day({"side": "LONG"}, regime_pnl_per_trade=2.5,
                                          now=cr_time(2026, 5, 5, 23, 0))
        assert result.passed is True
        assert "override" in result.reason.lower() or "ok" in result.reason.lower()

    def test_blocks_at_3am_low_quality(self, cr_time):
        result = vetos.veto_time_of_day({"side": "LONG"}, regime_pnl_per_trade=0.5,
                                          now=cr_time(2026, 5, 5, 3, 0))
        assert result.passed is False
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/punk_smart/test_vetos.py::TestTimeOfDayVeto -v
```

Expected: 4 FAIL.

- [ ] **Step 3: Write minimal implementation**

Append to `.claude/scripts/punk_smart_vetos.py`:

```python
def veto_time_of_day(setup: dict, regime_pnl_per_trade: float, now) -> VetoResult:
    cr_hour = now.astimezone(state.CR_OFFSET).hour
    in_weak = cr_hour >= 22 or cr_hour < 5
    if not in_weak:
        return VetoResult("time_of_day", True, f"CR {cr_hour:02d}:xx active window",
                          source="local clock")
    if regime_pnl_per_trade >= 2.0:
        return VetoResult("time_of_day", True,
                          f"CR {cr_hour:02d}:xx weak window — override (regime $/trade ≥2)",
                          source="local clock")
    return VetoResult("time_of_day", False,
                      f"CR {cr_hour:02d}:xx asian/weak window + low-quality regime",
                      source="local clock")
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/punk_smart/test_vetos.py -v
```

Expected: 18 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/punk_smart_vetos.py tests/punk_smart/test_vetos.py
git commit -m "feat(punk-smart-v2): veto #6 time-of-day weak window (soft)"
```

---

## Task 8: Veto evaluator (compose 6 vetos)

**Files:**
- Modify: `.claude/scripts/punk_smart_vetos.py`
- Modify: `tests/punk_smart/test_vetos.py`

The pipeline calls `evaluate(setup, ctx) → list[VetoResult]` honoring the `vetos_enabled` flag from mapping config.

- [ ] **Step 1: Write the failing test**

Append to `tests/punk_smart/test_vetos.py`:

```python
class TestEvaluate:
    def test_runs_all_enabled_vetos(self, tmp_profile_dir, cr_time, monkeypatch,
                                     signals_csv_factory):
        signals_csv_factory([])
        monkeypatch.setattr(vetos, "_macro_check",
                            lambda: {"blocked": False, "reason": None})
        monkeypatch.setattr(vetos, "_fng_now", lambda: 50)
        monkeypatch.setattr(vetos, "_funding_now", lambda asset: 0.0001)
        ctx = {
            "now": cr_time(2026, 5, 5, 10, 0),
            "memory_dir": tmp_profile_dir,
            "regime_pnl_per_trade": 2.5,
            "enabled": ["macro", "blacklist", "correlation", "sentiment",
                         "funding", "time_of_day"],
        }
        results = vetos.evaluate({"asset": "BTCUSDT", "side": "LONG"}, ctx)
        assert len(results) == 6
        assert all(r.passed for r in results)

    def test_skips_disabled_vetos(self, tmp_profile_dir, cr_time, monkeypatch,
                                   signals_csv_factory):
        signals_csv_factory([])
        monkeypatch.setattr(vetos, "_macro_check",
                            lambda: {"blocked": True, "reason": "FOMC"})
        ctx = {
            "now": cr_time(2026, 5, 5, 10, 0),
            "memory_dir": tmp_profile_dir,
            "regime_pnl_per_trade": 2.5,
            "enabled": ["blacklist", "correlation"],  # macro NOT in list
        }
        results = vetos.evaluate({"asset": "BTCUSDT", "side": "LONG"}, ctx)
        assert all(r.name in ("blacklist", "correlation") for r in results)
        assert all(r.passed for r in results)

    def test_first_failed_veto_is_blocking(self, tmp_profile_dir, cr_time,
                                            monkeypatch, signals_csv_factory):
        signals_csv_factory([
            {"symbol": "BTCUSDT.P", "side": "LONG", "exit_price": ""},
        ])
        monkeypatch.setattr(vetos, "_macro_check",
                            lambda: {"blocked": False, "reason": None})
        monkeypatch.setattr(vetos, "_fng_now", lambda: 50)
        monkeypatch.setattr(vetos, "_funding_now", lambda asset: 0.0001)
        ctx = {
            "now": cr_time(2026, 5, 5, 10, 0),
            "memory_dir": tmp_profile_dir,
            "regime_pnl_per_trade": 2.5,
            "enabled": ["macro", "correlation"],
        }
        results = vetos.evaluate({"asset": "ETHUSDT", "side": "LONG"}, ctx)
        # correlation should fail (BTC LONG already in btc_majors)
        failing = [r for r in results if not r.passed]
        assert len(failing) == 1
        assert failing[0].name == "correlation"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/punk_smart/test_vetos.py::TestEvaluate -v
```

Expected: 3 FAIL with `AttributeError: evaluate`.

- [ ] **Step 3: Write minimal implementation**

Append to `.claude/scripts/punk_smart_vetos.py`:

```python
def evaluate(setup: dict, ctx: dict) -> list[VetoResult]:
    """Run enabled vetos in fixed order. Returns one VetoResult per veto."""
    enabled = ctx.get("enabled", ["macro", "blacklist", "correlation",
                                    "sentiment", "funding", "time_of_day"])
    results: list[VetoResult] = []
    if "macro" in enabled:
        results.append(veto_macro(setup))
    if "blacklist" in enabled:
        results.append(veto_blacklist(setup, now=ctx["now"],
                                        memory_dir=ctx.get("memory_dir")))
    if "correlation" in enabled:
        results.append(veto_correlation(setup, memory_dir=ctx.get("memory_dir")))
    if "sentiment" in enabled:
        results.append(veto_sentiment(setup))
    if "funding" in enabled:
        results.append(veto_funding(setup))
    if "time_of_day" in enabled:
        results.append(veto_time_of_day(
            setup,
            regime_pnl_per_trade=ctx.get("regime_pnl_per_trade", 0.0),
            now=ctx["now"]))
    return results


def is_approved(results: list[VetoResult]) -> bool:
    return all(r.passed for r in results)
```

- [ ] **Step 4: Run all tests**

```bash
pytest tests/punk_smart/test_vetos.py -v
```

Expected: 21 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/punk_smart_vetos.py tests/punk_smart/test_vetos.py
git commit -m "feat(punk-smart-v2): veto evaluator (compose 6 vetos)"
```

---

## Task 9: Sizing helper (regime confidence → margin)

**Files:**
- Create: `.claude/scripts/regime_confidence.py`
- Test: `tests/punk_smart/test_regime_confidence.py`

- [ ] **Step 1: Write the failing test**

Create `tests/punk_smart/test_regime_confidence.py`:

```python
"""Tests for regime_confidence (position sizing helper)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".claude" / "scripts"))

import regime_confidence as rc


def test_ranging_high_quality_size():
    out = rc.compute(pnl_per_trade=2.68, base_margin=4.0)
    assert abs(out["size_mult"] - 1.34) < 0.01
    assert abs(out["margin_usd"] - 5.36) < 0.01
    assert abs(out["notional_10x"] - 53.60) < 0.1


def test_marginal_regime_clipped_at_min():
    out = rc.compute(pnl_per_trade=0.22, base_margin=4.0)
    assert out["size_mult"] == 0.30
    assert abs(out["margin_usd"] - 1.20) < 0.01


def test_huge_pnl_clipped_at_max():
    out = rc.compute(pnl_per_trade=10.0, base_margin=4.0)
    assert out["size_mult"] == 1.50


def test_negative_pnl_clipped_at_min():
    out = rc.compute(pnl_per_trade=-1.5, base_margin=4.0)
    assert out["size_mult"] == 0.30


def test_dynamic_disabled_returns_full_size():
    out = rc.compute(pnl_per_trade=0.5, base_margin=4.0, dynamic=False)
    assert out["size_mult"] == 1.0
    assert abs(out["margin_usd"] - 4.0) < 0.01
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/punk_smart/test_regime_confidence.py -v
```

Expected: 5 FAIL with `ModuleNotFoundError: regime_confidence`.

- [ ] **Step 3: Write minimal implementation**

Create `.claude/scripts/regime_confidence.py`:

```python
#!/usr/bin/env python3
"""regime_confidence — position sizing by regime backtest expectancy.

Formula: size_mult = clip(pnl_per_trade / 2.0, min=0.3, max=1.5)
"""

from __future__ import annotations

import argparse
import json

MIN_MULT = 0.30
MAX_MULT = 1.50
DIVISOR = 2.0
LEVERAGE = 10


def compute(pnl_per_trade: float, base_margin: float = 4.0,
            dynamic: bool = True) -> dict:
    if not dynamic:
        size_mult = 1.0
    else:
        raw = pnl_per_trade / DIVISOR
        size_mult = max(MIN_MULT, min(MAX_MULT, raw))
    margin = round(base_margin * size_mult, 2)
    return {
        "pnl_per_trade": pnl_per_trade,
        "size_mult": round(size_mult, 2),
        "margin_usd": margin,
        "notional_10x": round(margin * LEVERAGE, 2),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--pnl-per-trade", type=float, required=True)
    p.add_argument("--base-margin", type=float, default=4.0)
    p.add_argument("--no-dynamic", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    out = compute(args.pnl_per_trade, args.base_margin,
                  dynamic=not args.no_dynamic)
    if args.json:
        print(json.dumps(out))
    else:
        print(f"size_mult={out['size_mult']}  margin=${out['margin_usd']}  "
              f"notional={out['notional_10x']}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/punk_smart/test_regime_confidence.py -v
```

Expected: 5 PASS.

- [ ] **Step 5: Verify CLI works**

```bash
python3 .claude/scripts/regime_confidence.py --pnl-per-trade 2.68 --json
```

Expected: `{"pnl_per_trade": 2.68, "size_mult": 1.34, "margin_usd": 5.36, "notional_10x": 53.6}`

- [ ] **Step 6: Commit**

```bash
git add .claude/scripts/regime_confidence.py tests/punk_smart/test_regime_confidence.py
git commit -m "feat(punk-smart-v2): regime confidence sizing helper"
```

---

## Task 10: Backtest paginated fetch (60-day window)

**Files:**
- Modify: `.claude/scripts/backtest_regime_matrix.py`
- Test: `tests/punk_smart/test_backtest_paginated.py`

- [ ] **Step 1: Write the failing test**

Create `tests/punk_smart/test_backtest_paginated.py`:

```python
"""Tests for paginated Binance fetch."""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".claude" / "scripts"))

import backtest_regime_matrix as bt


def _mock_klines(num_bars: int, start_ts: int = 0):
    """Build a fake Binance klines response."""
    return [[start_ts + i * 900_000, "1.0", "1.5", "0.5", "1.2", "100.0", 0, 0, 0, 0, 0, 0]
            for i in range(num_bars)]


def test_paginated_fetch_returns_all_bars():
    """60d 15m → 5760 bars across 4 calls of 1500 each (last call short)."""
    expected_total = 96 * 60  # 5760

    call_count = {"n": 0}

    def fake_urlopen(req, timeout):
        call_count["n"] += 1
        # Each call returns at most 1500 bars, end-1500 of remaining range
        m = MagicMock()
        if call_count["n"] <= 3:
            payload = _mock_klines(1500, start_ts=call_count["n"] * 1_000_000)
        else:
            payload = _mock_klines(expected_total - 1500 * 3,
                                    start_ts=call_count["n"] * 1_000_000)
        m.read.return_value = bytes(__import__("json").dumps(payload), "utf-8")
        m.__enter__ = lambda s: s
        m.__exit__ = lambda *a: None
        return m

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        bars = bt.fetch_paginated("BTCUSDT", "15m", days=60)

    assert len(bars) == expected_total
    assert call_count["n"] == 4


def test_paginated_dedup_overlap():
    """When pages overlap by 1 bar, output should dedup by timestamp."""
    def fake_urlopen(req, timeout):
        # Always return the same 100-bar payload
        m = MagicMock()
        m.read.return_value = bytes(
            __import__("json").dumps(_mock_klines(100, start_ts=0)), "utf-8")
        m.__enter__ = lambda s: s
        m.__exit__ = lambda *a: None
        return m

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        bars = bt.fetch_paginated("BTCUSDT", "15m", days=1)

    # No duplicate timestamps
    ts = [b["t"] for b in bars]
    assert len(ts) == len(set(ts))
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/punk_smart/test_backtest_paginated.py -v
```

Expected: 2 FAIL with `AttributeError: fetch_paginated`.

- [ ] **Step 3: Write minimal implementation**

In `.claude/scripts/backtest_regime_matrix.py`, add (do not replace existing `fetch`):

```python
def fetch_paginated(symbol: str, interval: str, days: int) -> list[dict]:
    """Fetch up to `days` of bars by paginating Binance klines (1500-bar cap).

    Strategy: walk forward in time, oldest-first, using endTime cursor.
    De-duplicate by timestamp.
    """
    bars_per_day = {"15m": 96, "1h": 24, "4h": 6}.get(interval, 96)
    target = bars_per_day * days
    seen: dict[int, dict] = {}

    # Start from now-(days), walk forward
    end_ts = None  # None = "now" on Binance
    while len(seen) < target:
        url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit=1500"
        if end_ts is not None:
            url += f"&endTime={end_ts}"
        try:
            with urllib.request.urlopen(url, timeout=20) as resp:
                page = json.loads(resp.read())
        except Exception as e:
            print(f"  WARN paginated {symbol}: {e}", file=sys.stderr)
            break
        if not page:
            break
        for b in page:
            t = int(b[0])
            seen[t] = {"t": t, "o": float(b[1]), "h": float(b[2]),
                        "l": float(b[3]), "c": float(b[4]), "v": float(b[5])}
        # Move cursor: endTime = oldest bar in this page minus 1ms
        oldest = min(int(b[0]) for b in page)
        if end_ts is not None and oldest >= end_ts:
            break  # no progress (pagination saturated)
        end_ts = oldest - 1
        # Brief pause to avoid rate limits — keep modest
        time.sleep(0.1)
        if len(page) < 1500:
            break  # exchange returned less than max → reached the start

    bars = sorted(seen.values(), key=lambda b: b["t"])
    return bars[-target:] if len(bars) > target else bars
```

Also add at the top of the file:

```python
import time
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/punk_smart/test_backtest_paginated.py -v
```

Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/backtest_regime_matrix.py tests/punk_smart/test_backtest_paginated.py
git commit -m "feat(punk-smart-v2): paginated Binance fetch (60-day window)"
```

---

## Task 11: Backtest — per-asset cells + schema v2 mapping

**Files:**
- Modify: `.claude/scripts/backtest_regime_matrix.py`

This is a refactor of `main()` and is too large for a strict TDD cycle without scaffolding the entire backtest run. The integration test is the real backtest run in Task 14.

- [ ] **Step 1: Modify the matrix tracker to also track per-asset cells**

Open `.claude/scripts/backtest_regime_matrix.py`. Find the line:

```python
cells = {r: {s: [] for s in STRATS} for r in REGIMES}
```

Add immediately after it:

```python
# Per-asset cells: cells_per_asset[asset][regime][strategy] = list of trades
cells_per_asset: dict = {a: {r: {s: [] for s in STRATS} for r in REGIMES + ["UNKNOWN", "MIXED"]}
                          for a in ASSETS}
```

- [ ] **Step 2: Append trades to per-asset cells**

In the inner loop where the existing line `cells[regime][sname].append(...)` lives, add:

```python
                cells_per_asset[sym][regime][sname].append({"asset": sym, **setup, **result})
```

- [ ] **Step 3: Switch the asset fetch to paginated 60-day**

Find the lines:

```python
        b15 = fetch(sym, "15m", min(1500, 96 * DAYS))
        b1h = fetch(sym, "1h", min(1500, 24 * DAYS + 60))
```

Replace with:

```python
        b15 = fetch_paginated(sym, "15m", days=DAYS)
        b1h = fetch_paginated(sym, "1h", days=DAYS + 3)  # +3d cushion for 1h aggregations
```

And change `DAYS = 15` (top of file) to `DAYS = 60`.

- [ ] **Step 4: Build per-asset mapping when emitting JSON**

After the existing block that builds `mapping = {}`, add:

```python
    per_asset_mapping: dict = {}
    for asset in ASSETS:
        per_asset_mapping[asset] = {}
        for regime in REGIMES + ["UNKNOWN", "MIXED"]:
            best = None
            best_pnl = -9999
            for sname in STRATS:
                ts = cells_per_asset[asset][regime][sname]
                if len(ts) < 10:  # threshold raised from 5 thanks to 60-day data
                    continue
                pnl = sum(t["pnl_usd"] for t in ts)
                if pnl > best_pnl:
                    best_pnl = pnl
                    best = sname
            if best:
                ts = cells_per_asset[asset][regime][best]
                wr = sum(1 for t in ts if t["pnl_usd"] > 0) / len(ts) * 100
                if best_pnl > 0:  # only positive cells get promoted
                    per_asset_mapping[asset][regime] = {
                        "strategy": best, "n_trades": len(ts),
                        "wr": wr, "pnl": best_pnl,
                        "pnl_per_trade": best_pnl / len(ts),
                    }
        if not per_asset_mapping[asset]:
            del per_asset_mapping[asset]  # don't write empty entries
```

- [ ] **Step 5: Update the JSON write to use schema v2**

Find:

```python
    out_file.write_text(json.dumps(mapping, indent=2))
```

Replace with:

```python
    schema_v2 = {
        "version": 2,
        "vetos_enabled": ["macro", "blacklist", "correlation", "sentiment",
                            "funding", "time_of_day"],
        "dynamic_sizing": True,
        "trail_sl_offset_atr": 0.2,
        "global": mapping,
        "per_asset": per_asset_mapping,
    }
    out_file.write_text(json.dumps(schema_v2, indent=2))
```

- [ ] **Step 6: Smoke-check the script imports**

```bash
python3 -c "import sys; sys.path.insert(0, '.claude/scripts'); import backtest_regime_matrix as bt; print(bt.fetch_paginated, bt.classify_regime)"
```

Expected: prints two function references, no error.

- [ ] **Step 7: Commit**

```bash
git add .claude/scripts/backtest_regime_matrix.py
git commit -m "feat(punk-smart-v2): per-asset cells + schema v2 mapping output"
```

---

## Task 12: Backtest — trail SL in simulate()

**Files:**
- Modify: `.claude/scripts/backtest_regime_matrix.py`

- [ ] **Step 1: Locate the `simulate()` function**

It starts around line 350. Read it fully.

- [ ] **Step 2: Modify simulate to apply trail SL after TP1 hit**

Replace the body of `simulate()` with:

```python
def simulate(setup, future_bars, max_bars=24, trail_sl_offset_atr: float = 0.2):
    if setup is None:
        return None
    e = setup["entry"]; sl = setup["sl"]; tp1 = setup["tp1"]; tp2 = setup["tp2"]
    side = setup["side"]
    duration = 0
    sl_hit = tp1_hit = tp2_hit = False
    sl_active = sl  # mutable: shifts to BE+offset after TP1
    # Approximate ATR from setup distances (tp1-entry as proxy for half-ATR scale)
    atr_proxy = abs(tp1 - e)
    trail_sl = (e + trail_sl_offset_atr * atr_proxy) if side == "LONG" \
               else (e - trail_sl_offset_atr * atr_proxy)
    for k, bar in enumerate(future_bars[:max_bars]):
        duration = (k + 1) * 15
        if side == "SHORT":
            if bar["h"] >= sl_active:
                sl_hit = True; break
            if bar["l"] <= tp2 and not tp2_hit: tp2_hit = True
            if bar["l"] <= tp1 and not tp1_hit:
                tp1_hit = True
                sl_active = trail_sl  # move SL to BE - 0.2*ATR
        else:
            if bar["l"] <= sl_active:
                sl_hit = True; break
            if bar["h"] >= tp2 and not tp2_hit: tp2_hit = True
            if bar["h"] >= tp1 and not tp1_hit:
                tp1_hit = True
                sl_active = trail_sl  # move SL to BE + 0.2*ATR
        if tp2_hit:
            break
    if sl_hit and not tp1_hit:
        pnl_pct = -abs(sl - e) / e
        outcome = "SL"
    elif tp2_hit:
        d1 = abs(tp1 - e) / e
        d2 = abs(tp2 - e) / e
        pnl_pct = d1 * 0.5 + d2 * 0.5
        outcome = "TP2"
    elif tp1_hit and sl_hit:
        # TP1 hit then SL on trail (locks small profit)
        d1 = abs(tp1 - e) / e
        trail_lock = trail_sl_offset_atr * atr_proxy / e
        pnl_pct = d1 * 0.5 + trail_lock * 0.5
        outcome = "TP1_TRAIL_SL"
    elif tp1_hit:
        d1 = abs(tp1 - e) / e
        pnl_pct = d1 * 0.5  # 50% TP1, 50% riding (timeout)
        outcome = "TP1"
    else:
        if len(future_bars) >= max_bars:
            last_c = future_bars[max_bars - 1]["c"]
            pnl_pct = (e - last_c) / e if side == "SHORT" else (last_c - e) / e
        outcome = "TIMEOUT"
    pnl_usd = pnl_pct * NOTIONAL - (NOTIONAL * FEES_PCT / 100)
    return {"outcome": outcome, "pnl_usd": pnl_usd, "duration_min": duration}
```

- [ ] **Step 3: Verify the script still imports and the function exists**

```bash
python3 -c "import sys; sys.path.insert(0, '.claude/scripts'); from backtest_regime_matrix import simulate; r = simulate({'side':'LONG','entry':100.0,'sl':99.0,'tp1':102.0,'tp2':104.0},[{'h':103.0,'l':99.5,'c':102.5},{'h':104.5,'l':101.0,'c':104.0}]); print(r)"
```

Expected: prints a dict with `"outcome": "TP2"` (or similar), no errors.

- [ ] **Step 4: Commit**

```bash
git add .claude/scripts/backtest_regime_matrix.py
git commit -m "feat(punk-smart-v2): trail SL @ BE+0.2×ATR in backtest simulate"
```

---

## Task 13: Run 60-day backtest, save findings doc

**Files:**
- Run: `.claude/scripts/backtest_regime_matrix.py`
- Generate: `.claude/scripts/regime_mapping.json` (v2 format)
- Backup: `.claude/scripts/regime_mapping.v1.backup`
- Generate: `docs/backtest_findings_2026-05-05_punk_smart_v2.md`

- [ ] **Step 1: Backup v1 mapping**

```bash
cp .claude/scripts/regime_mapping.json .claude/scripts/regime_mapping.v1.backup
git add .claude/scripts/regime_mapping.v1.backup
git commit -m "chore(punk-smart-v2): backup v1 mapping before regen"
```

- [ ] **Step 2: Run the 60-day backtest**

```bash
python3 .claude/scripts/backtest_regime_matrix.py 2>&1 | tee /tmp/backtest_v2_run.txt
```

Expected: takes 5-15 min (paginated fetch × 9 assets × 2 timeframes). Prints matrix, mapping, and summary at the end. Writes to `.claude/scripts/regime_mapping.json` in schema v2.

If it fails: read the WARN lines in the output, identify which symbol failed pagination, and inspect rate-limit responses.

- [ ] **Step 3: Verify the new mapping is schema v2**

```bash
python3 -c "import json; m = json.loads(open('.claude/scripts/regime_mapping.json').read()); print('version:', m.get('version')); print('per_asset keys:', list(m.get('per_asset', {}).keys())); print('global keys:', list(m.get('global', {}).keys()))"
```

Expected: `version: 2`, ≥3 per_asset assets, ≥5 global regimes.

- [ ] **Step 4: Write the findings doc**

Create `docs/backtest_findings_2026-05-05_punk_smart_v2.md` with this template (fill in actual numbers from `/tmp/backtest_v2_run.txt`):

```markdown
# Backtest findings — /punk-smart v2 (60-day, schema v2)

**Date:** 2026-05-05
**Window:** 60 days, 9 assets, paginated Binance fetch
**Margin:** $100 × 10x leverage
**Trail SL:** 0.2×ATR after TP1 hit

## Top-line metrics

| Metric | v1 baseline (15d) | v2 (60d) | Δ | Gate |
|---|---|---|---|---|
| WR | 49.4% | XX.X% | ±X.X | ≥53% |
| Profit factor | n/a | X.XX | — | ≥1.4 |
| Max-DD | n/a | X.X% | — | ≤20% |
| Trades/day | 5.1 | X.X | ±X.X | ≥2.5 |
| PnL/day | +$10.5 | +$X.XX | ±X.XX | ≥+$6.5 |
| PnL absolute | +$157.61 (15d) | +$XXX.XX (60d) | — | ≥+$390 |

## Per-asset highlights

(table of top 5 (asset, regime) cells with n≥10)

## Mapping changes (v1 → v2)

(diff of regime → strategy assignments, per-asset overrides newly active)

## Open questions / follow-ups

(anything surprising)
```

Run the doc through any clarity pass that the existing `elements-of-style:writing-clearly-and-concisely` skill applies.

- [ ] **Step 5: Commit**

```bash
git add docs/backtest_findings_2026-05-05_punk_smart_v2.md .claude/scripts/regime_mapping.json
git commit -m "feat(punk-smart-v2): 60-day backtest results + schema v2 mapping"
```

---

## Task 14: Router refactor — pipeline stage 0 + 1 (kill-switch + per-asset lookup)

**Files:**
- Modify: `.claude/scripts/punk_smart_router.py`

- [ ] **Step 1: Read the file fully**

```bash
wc -l .claude/scripts/punk_smart_router.py
```

(176 lines per spec — small, read it all first.)

- [ ] **Step 2: Add the kill-switch + mapping lookup helpers**

Replace the imports and `load_mapping()`/`evaluate_asset()` with:

```python
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backtest_regime_matrix import (
    fetch, calc_atr, calc_rsi, calc_ema, calc_macd, calc_bb, calc_adx, calc_vwap,
    classify_regime, strat_a_vwap, strat_b_trending_pullback,
)
import punk_smart_state as state
import punk_smart_vetos as vetos
import regime_confidence as rc

CR_OFFSET = state.CR_OFFSET
ASSETS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "MSTRUSDT", "AVAXUSDT",
          "INJUSDT", "DOGEUSDT", "WIFUSDT", "XLMUSDT"]

STRATEGY_FNS = {
    "A_VWAP": strat_a_vwap,
    "B_TrendPullback": strat_b_trending_pullback,
}

MAPPING_FILE = Path(__file__).parent / "regime_mapping.json"


def load_mapping() -> dict:
    if not MAPPING_FILE.exists():
        print(f"❌ Mapping not found: {MAPPING_FILE}", file=sys.stderr)
        sys.exit(1)
    return json.loads(MAPPING_FILE.read_text())


def lookup_regime_info(mapping: dict, asset: str, regime: str) -> dict | None:
    """Schema v2 lookup: per-asset → global → None."""
    # Schema v1 fallback
    if mapping.get("version") != 2:
        info = mapping.get(regime)
        if info and info.get("pnl", 0) > 0:
            return {**info, "tier": "global"}
        return None
    per_asset = mapping.get("per_asset", {}).get(asset, {})
    if regime in per_asset:
        cell = per_asset[regime]
        if cell.get("n_trades", 0) >= 10 and cell.get("pnl_per_trade", 0) > 0:
            return {**cell, "tier": "per_asset"}
        return {"_stand_aside": True,
                 "reason": f"per-asset cell for {asset} {regime} pnl_per_trade ≤ 0"}
    g = mapping.get("global", {}).get(regime)
    if g and g.get("pnl_per_trade", 0) > 0:
        return {**g, "tier": "global"}
    return None
```

- [ ] **Step 3: Add stage 0 to main**

Insert at the top of `main()` (after `args = p.parse_args()`):

```python
    mapping = load_mapping()

    # STAGE 0: kill-switch
    now = datetime.now(CR_OFFSET)
    active, reason = state.is_kill_switch_active(now)
    if active:
        print(f"🚫 PUNK-SMART PAUSED — {reason}", file=sys.stderr)
        if args.json:
            print(json.dumps({"status": "PAUSED", "reason": reason}))
        else:
            print(f"\n🚫 PAUSED — {reason}\n")
            print("Override (conscious decision): "
                  "python3 .claude/scripts/punk_smart_state.py --reset-killswitch")
        return
```

- [ ] **Step 4: Replace `evaluate_asset` with v2 lookup**

```python
def evaluate_asset(symbol: str, mapping: dict, now: datetime) -> dict:
    bars_15m = fetch(symbol, "15m", 100)
    bars_1h = fetch(symbol, "1h", 80)
    if len(bars_15m) < 70 or len(bars_1h) < 50:
        return {"asset": symbol, "status": "INSUFFICIENT_DATA"}
    i = len(bars_15m) - 1
    regime = classify_regime(bars_15m, bars_1h, i)
    base = {"asset": symbol, "regime": regime, "now_price": bars_15m[-1]["c"]}

    info = lookup_regime_info(mapping, symbol, regime)
    if info is None:
        return {**base, "status": "STAND_ASIDE",
                "reason": f"regime {regime} not tradeable in mapping"}
    if info.get("_stand_aside"):
        return {**base, "status": "STAND_ASIDE",
                "reason": info["reason"], "tier": "per_asset"}

    strategy_name = info["strategy"]
    strat_fn = STRATEGY_FNS.get(strategy_name)
    if strat_fn is None:
        return {**base, "status": "STRATEGY_UNAVAILABLE",
                "strategy": strategy_name}
    setup = strat_fn(bars_15m, bars_1h, i)
    if setup is None:
        return {
            **base, "status": "NO_SETUP", "strategy": strategy_name,
            "reason": f"strategy {strategy_name} no triggea en este momento",
            "backtest_wr": round(info["wr"], 1),
            "backtest_pnl_per_trade": round(info["pnl_per_trade"], 2),
            "tier": info["tier"],
        }

    # Tentative — vetos applied later in main()
    rr_tp1 = abs(setup["tp1"] - setup["entry"]) / abs(setup["sl"] - setup["entry"])
    rr_tp2 = abs(setup["tp2"] - setup["entry"]) / abs(setup["sl"] - setup["entry"])
    return {
        **base, "status": "TENTATIVE",
        "strategy": strategy_name,
        "tier": info["tier"],
        "side": setup["side"],
        "entry": round(setup["entry"], 4),
        "sl": round(setup["sl"], 4),
        "tp1": round(setup["tp1"], 4),
        "tp2": round(setup["tp2"], 4),
        "rr_tp1": round(rr_tp1, 2),
        "rr_tp2": round(rr_tp2, 2),
        "sl_distance_pct": round(abs(setup["sl"] - setup["entry"]) / setup["entry"] * 100, 3),
        "tp1_distance_pct": round(abs(setup["tp1"] - setup["entry"]) / setup["entry"] * 100, 3),
        "tp2_distance_pct": round(abs(setup["tp2"] - setup["entry"]) / setup["entry"] * 100, 3),
        "backtest_wr": round(info["wr"], 1),
        "backtest_pnl_per_trade": round(info["pnl_per_trade"], 2),
        "_atr_15m": calc_atr(bars_15m),
    }
```

- [ ] **Step 5: Smoke-check imports**

```bash
python3 -c "import sys; sys.path.insert(0, '.claude/scripts'); import punk_smart_router as r; m = r.load_mapping(); print('mapping keys:', list(m.keys())[:5])"
```

Expected: `mapping keys: ['version', 'vetos_enabled', 'dynamic_sizing', 'trail_sl_offset_atr', 'global']`

- [ ] **Step 6: Commit**

```bash
git add .claude/scripts/punk_smart_router.py
git commit -m "feat(punk-smart-v2): router stages 0+1 (kill-switch + v2 lookup)"
```

---

## Task 15: Router refactor — pipeline stage 3 + 4 + 5 (vetos + sizing + trail)

**Files:**
- Modify: `.claude/scripts/punk_smart_router.py`

- [ ] **Step 1: Replace the `main()` body's loop with the full pipeline**

Find the main scanning loop. Replace the section after stage 0 (after the `if active: ... return` block) with:

```python
    targets = [args.asset] if args.asset else ASSETS
    raw_results = [evaluate_asset(s, mapping, now) for s in targets]

    enabled = mapping.get("vetos_enabled",
                          ["macro", "blacklist", "correlation", "sentiment",
                            "funding", "time_of_day"])
    dynamic = mapping.get("dynamic_sizing", True)
    trail_offset = mapping.get("trail_sl_offset_atr", 0.2)

    approved: list[dict] = []
    vetoed: list[dict] = []
    no_setup: list[dict] = []
    stand_aside: list[dict] = []

    for r in raw_results:
        status = r.get("status")
        if status == "STAND_ASIDE":
            stand_aside.append(r); continue
        if status in ("INSUFFICIENT_DATA", "STRATEGY_UNAVAILABLE"):
            stand_aside.append(r); continue
        if status == "NO_SETUP":
            no_setup.append(r); continue
        if status != "TENTATIVE":
            continue  # safety

        # Stage 3: vetos
        ctx = {
            "now": now,
            "memory_dir": None,
            "regime_pnl_per_trade": r.get("backtest_pnl_per_trade", 0.0),
            "enabled": enabled,
        }
        veto_results = vetos.evaluate(
            {"asset": r["asset"], "side": r["side"]}, ctx)
        r["vetos"] = [{"name": v.name, "passed": v.passed,
                        "reason": v.reason} for v in veto_results]
        if not vetos.is_approved(veto_results):
            r["status"] = "VETOED"
            vetoed.append(r); continue

        # Stage 4: sizing
        sizing = rc.compute(r["backtest_pnl_per_trade"],
                             base_margin=4.0, dynamic=dynamic)
        r["sizing"] = sizing

        # Stage 5: trail SL annotation
        atr = r.pop("_atr_15m", 0.0)
        if r["side"] == "LONG":
            be_trail = r["entry"] + trail_offset * atr
        else:
            be_trail = r["entry"] - trail_offset * atr
        r["trail_sl"] = round(be_trail, 4)
        r["trail_sl_offset_atr"] = trail_offset
        r["atr_15m"] = round(atr, 4)
        r["status"] = "APPROVED"
        approved.append(r)
```

- [ ] **Step 2: Update output rendering**

Replace the printing block in `main()` with:

```python
    if args.json:
        print(json.dumps({
            "status": "OK",
            "approved": approved,
            "vetoed": vetoed,
            "no_setup": no_setup,
            "stand_aside": stand_aside,
            "mapping_version": mapping.get("version", 1),
        }, indent=2, default=str))
        return

    print(f"\n{'='*72}")
    print(f"PUNK-SMART v2 — {now.strftime('%H:%M CR')}  |  mapping v{mapping.get('version', 1)}")
    print(f"{'='*72}")

    if approved:
        approved.sort(key=lambda x: -x["rr_tp2"])
        print(f"\n✅ {len(approved)} APPROVED setup(s):\n")
        for i, s in enumerate(approved):
            arrow = "🟢 LONG" if s["side"] == "LONG" else "🔴 SHORT"
            print(f"#{i+1} {arrow} {s['asset']}  (regime: {s['regime']}, "
                  f"strategy: {s['strategy']}, tier: {s.get('tier','global')})")
            print(f"   Entry: {s['entry']}   |   BT WR {s['backtest_wr']}%, "
                  f"${s['backtest_pnl_per_trade']:+.2f}/trade")
            print(f"   SL:  {s['sl']} ({s['sl_distance_pct']}%)")
            print(f"   TP1: {s['tp1']} ({s['tp1_distance_pct']}%) — R:R {s['rr_tp1']}")
            print(f"   TP2: {s['tp2']} ({s['tp2_distance_pct']}%) — R:R {s['rr_tp2']}")
            sz = s["sizing"]
            print(f"   Size: ${sz['margin_usd']} margin × 10x = ${sz['notional_10x']} "
                  f"notional   (mult {sz['size_mult']})")
            print(f"   DUREX: TP1 hit → move SL to {s['trail_sl']} "
                  f"(BE + {s['trail_sl_offset_atr']}×ATR)")
            print()
    else:
        print("\n⏳ NO APPROVED setups right now.")

    if vetoed:
        print(f"\n{'─'*72}\n❌ {len(vetoed)} VETOED setup(s):")
        for s in vetoed:
            print(f"  {s['asset']:14s} {s['side']:5s} regime={s['regime']:18s}")
            for v in s["vetos"]:
                mark = "✓" if v["passed"] else "✗"
                print(f"      {mark} {v['name']:12s} {v['reason']}")

    if args.show_all:
        if no_setup:
            print(f"\n{'─'*72}\nNo setup ({len(no_setup)} assets):")
            for s in no_setup:
                print(f"  {s['asset']:14s} regime={s['regime']:18s} "
                      f"strategy={s.get('strategy','-'):16s}")
        if stand_aside:
            print(f"\n{'─'*72}\nStand aside ({len(stand_aside)} assets):")
            for s in stand_aside:
                print(f"  {s['asset']:14s} regime={s.get('regime','—'):18s} "
                      f"reason: {s.get('reason','')}")
```

- [ ] **Step 3: Smoke-check the script runs end-to-end**

```bash
python3 .claude/scripts/punk_smart_router.py --json 2>&1 | python3 -m json.tool | head -30
```

Expected: valid JSON with `status: "OK"` (or PAUSED if SLs were logged), `approved: [...]`, etc.

- [ ] **Step 4: Smoke-check the human format**

```bash
python3 .claude/scripts/punk_smart_router.py 2>&1 | head -40
```

Expected: dashboard with header `PUNK-SMART v2 — HH:MM CR | mapping v2`.

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/punk_smart_router.py
git commit -m "feat(punk-smart-v2): router stages 3+4+5 (vetos + sizing + trail)"
```

---

## Task 16: Hook /log-outcome to update state

**Files:**
- Modify: `.claude/scripts/bitunix_log.py`

- [ ] **Step 1: Locate `cmd_append_outcome`**

```bash
grep -n "def cmd_append_outcome" .claude/scripts/bitunix_log.py
```

Should be around line 350-355.

- [ ] **Step 2: Add state update after successful CSV write**

In `cmd_append_outcome`, find this block:

```python
    print(f"bitunix_log: closed {args.symbol} with {args.outcome} at {_fmt_price(args.exit_price)}")
    return 0
```

Insert immediately before that print:

```python
    # Hook for /punk-smart v2 state machine
    try:
        import punk_smart_state as _state
        from datetime import datetime as _dt
        sym_norm = args.symbol.replace(".P", "").upper()
        now = _dt.now(_state.CR_OFFSET)
        if args.outcome == "SL":
            _state.record_sl(sym_norm, now,
                              pnl_usd=(args.pnl if args.pnl is not None else 0.0))
        elif args.outcome.startswith("TP"):
            _state.record_tp(sym_norm, now)
    except Exception as e:
        log_error(f"punk_smart_state hook failed: {e}")
```

- [ ] **Step 3: Test the hook end-to-end (manual smoke)**

```bash
WALLY_PROFILE=bitunix python3 -c "
import sys; sys.path.insert(0, '.claude/scripts')
import punk_smart_state as state
from datetime import datetime
now = datetime.now(state.CR_OFFSET)
state.record_sl('TESTUSDT', now, pnl_usd=-3.0)
state.record_sl('TESTUSDT', now, pnl_usd=-3.0)
print('blacklisted:', state.is_blacklisted('TESTUSDT', now))
print('killswitch:', state.is_kill_switch_active(now))
state.reset_killswitch()
"
```

Expected: prints `blacklisted: True` and `killswitch: (True, '...')`. Then resets cleanly.

- [ ] **Step 4: Clean test state after smoke**

```bash
rm -f .claude/profiles/bitunix/memory/asset_sl_streaks.json .claude/profiles/bitunix/memory/sl_window.json
```

(So real `/punk-smart` runs aren't polluted by test data.)

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/bitunix_log.py
git commit -m "feat(punk-smart-v2): hook /log-outcome to state machine"
```

---

## Task 17: launchd daily reset

**Files:**
- Create: `.claude/launchd/com.wally.bitunix-daily-reset.plist`
- Create: `.claude/scripts/bitunix_daily_reset.sh`

- [ ] **Step 1: Create the reset script**

Create `.claude/scripts/bitunix_daily_reset.sh`:

```bash
#!/bin/bash
# Reset bitunix per-day state files at CR 00:00.
# Triggered by launchd com.wally.bitunix-daily-reset.

set -euo pipefail
ROOT="${HOME}/Documents/wally-trader"
MEM="${ROOT}/.claude/profiles/bitunix/memory"

# Truncate streaks file (keep schema)
cat > "${MEM}/asset_sl_streaks.json" <<EOF
{"version": 1, "as_of_cr_date": "$(date -u +%Y-%m-%d)", "assets": {}}
EOF

# Truncate window file
cat > "${MEM}/sl_window.json" <<EOF
{"events": [], "kill_switch_active_until": null}
EOF

echo "[$(date)] bitunix daily-reset done" >> "${ROOT}/.claude/logs/bitunix_reset.log"
```

```bash
chmod +x .claude/scripts/bitunix_daily_reset.sh
mkdir -p .claude/logs
```

- [ ] **Step 2: Create the plist**

Create `.claude/launchd/com.wally.bitunix-daily-reset.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.wally.bitunix-daily-reset</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/Users/josecampos/Documents/wally-trader/.claude/scripts/bitunix_daily_reset.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>6</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/wally-bitunix-reset.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/wally-bitunix-reset.err</string>
</dict>
</plist>
```

(StartCalendarInterval Hour=6 in UTC = 00:00 CR.)

- [ ] **Step 3: Test the reset script manually**

```bash
.claude/scripts/bitunix_daily_reset.sh
cat .claude/profiles/bitunix/memory/asset_sl_streaks.json
cat .claude/profiles/bitunix/memory/sl_window.json
```

Expected: both files contain empty defaults.

- [ ] **Step 4: Commit**

```bash
git add .claude/scripts/bitunix_daily_reset.sh .claude/launchd/com.wally.bitunix-daily-reset.plist
git commit -m "feat(punk-smart-v2): launchd daily reset for state files"
```

- [ ] **Step 5: Activate launchd** (manual — don't commit; user does this once on their machine)

User runs:
```bash
cp .claude/launchd/com.wally.bitunix-daily-reset.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.wally.bitunix-daily-reset.plist
```

---

## Task 18: Out-of-sample validation (70/30 split)

**Files:**
- Run: `.claude/scripts/backtest_split.py`
- Append to: `docs/backtest_findings_2026-05-05_punk_smart_v2.md`

- [ ] **Step 1: Inspect what backtest_split.py expects as input**

```bash
.claude/scripts/.venv/bin/python .claude/scripts/backtest_split.py --help 2>&1 | head -20
```

- [ ] **Step 2: Build train/test inputs from the 60-day backtest data**

Add a flag `--split` to `backtest_regime_matrix.py` that re-runs only with the train portion (first 42d) and outputs to a different mapping file. (If the existing helper takes raw metrics, use that path instead — read its source first.)

If `backtest_split.py` is helper-style (takes metric dicts), construct them from the backtest run:

```python
python3 - <<'EOF'
import json, subprocess, sys
sys.path.insert(0, '.claude/scripts')
from backtest_regime_matrix import (
    fetch_paginated, classify_regime, simulate, ASSETS, MARGIN, LEVERAGE,
    FEES_PCT, strat_a_vwap, strat_b_trending_pullback,
)

# Re-run the matrix in two passes: train (first 70%) and test (last 30%).
# Compute aggregate metrics for each.
# (Pseudo-code: actual implementation depends on backtest_split.py contract.)
EOF
```

If this requires more than 30 lines of glue, instead **add `--out-of-sample` flag to `backtest_regime_matrix.py` that runs train and test separately and emits a JSON report**. Treat that as an extension of Task 11.

- [ ] **Step 3: Run OOS evaluation**

Whichever the integration path, ensure:

```bash
python3 .claude/scripts/backtest_split.py --train '<train.json>' --test '<test.json>' 2>&1 | tee /tmp/oos_v2.txt
```

Output should declare PASS / WARN / FAIL.

- [ ] **Step 4: Append OOS result to findings doc**

Add a section to `docs/backtest_findings_2026-05-05_punk_smart_v2.md`:

```markdown
## Out-of-sample (70/30 split)

- Train (42d): WR XX.X%, PF X.XX, +$XXX
- Test (18d): WR XX.X%, PF X.XX, +$XXX
- Drift: WR ±X.X pp, PF ±X.XX
- Verdict: PASS / WARN / FAIL
```

- [ ] **Step 5: Commit**

```bash
git add docs/backtest_findings_2026-05-05_punk_smart_v2.md
git commit -m "feat(punk-smart-v2): out-of-sample 70/30 validation"
```

If verdict is **FAIL** or **WARN with significant drift (>30%)**, stop here and reassess vetos / mapping before proceeding to Task 19.

---

## Task 19: Live smoke test + acceptance gate

**Files:**
- Run: `.claude/scripts/punk_smart_router.py`

- [ ] **Step 1: Invoke /punk-smart in human format**

```bash
WALLY_PROFILE=bitunix python3 .claude/scripts/punk_smart_router.py 2>&1 | tee /tmp/punk_smart_v2_live.txt
```

Expected: dashboard prints. No tracebacks. At least one of {APPROVED, VETOED, NO_SETUP, STAND_ASIDE} list is populated.

- [ ] **Step 2: Invoke /punk-smart in JSON format**

```bash
WALLY_PROFILE=bitunix python3 .claude/scripts/punk_smart_router.py --json 2>&1 | python3 -m json.tool | head -40
```

Expected: parses as valid JSON.

- [ ] **Step 3: Verify acceptance gates from spec**

Check that the findings doc shows all 6 gates met (refer to spec table):

| Metric | Gate min | Result | Pass? |
|---|---|---|---|
| WR | ≥53% | X.X% | ? |
| PF | ≥1.4 | X.XX | ? |
| Max-DD | ≤20% | X% | ? |
| Trades/day | ≥2.5 | X.X | ? |
| PnL/day | ≥+$6.5 | +$X | ? |
| PnL absolute 60d | ≥+$390 | +$X | ? |

If **any gate fails**, do NOT proceed to merge. Revisit veto thresholds (likely funding ±0.05% may be too lax — try ±0.03%) or sizing formula (try clip [0.4, 1.6]).

- [ ] **Step 4: Append acceptance result to findings doc**

```markdown
## Acceptance gates

(filled-in table from above)

- All gates pass: YES/NO
- Decision: MERGE / RETUNE
```

- [ ] **Step 5: Commit**

```bash
git add docs/backtest_findings_2026-05-05_punk_smart_v2.md
git commit -m "feat(punk-smart-v2): live smoke test + acceptance gate verdict"
```

---

## Task 20: Rollback verification

Verify each rollback path declared in the spec works.

- [ ] **Step 1: Test schema-version rollback**

```bash
cp .claude/scripts/regime_mapping.json /tmp/v2_mapping_backup.json
cp .claude/scripts/regime_mapping.v1.backup .claude/scripts/regime_mapping.json
python3 .claude/scripts/punk_smart_router.py 2>&1 | head -10
cp /tmp/v2_mapping_backup.json .claude/scripts/regime_mapping.json
```

Expected: with v1 mapping, router prints v1-style output (no APPROVED/VETOED split, no per_asset tier label). No traceback.

- [ ] **Step 2: Test veto-individual disable**

```bash
python3 - <<'EOF'
import json
m = json.loads(open(".claude/scripts/regime_mapping.json").read())
m["vetos_enabled"] = ["macro"]  # only macro, all others off
open(".claude/scripts/regime_mapping.json", "w").write(json.dumps(m, indent=2))
EOF
python3 .claude/scripts/punk_smart_router.py 2>&1 | head -20
# Restore
git checkout .claude/scripts/regime_mapping.json
```

Expected: dashboard runs with only "macro" listed in any VETOED row's veto trace.

- [ ] **Step 3: Test sizing dynamic disable**

```bash
python3 - <<'EOF'
import json
m = json.loads(open(".claude/scripts/regime_mapping.json").read())
m["dynamic_sizing"] = False
open(".claude/scripts/regime_mapping.json", "w").write(json.dumps(m, indent=2))
EOF
python3 .claude/scripts/punk_smart_router.py 2>&1 | grep -i "Size: " | head -3
git checkout .claude/scripts/regime_mapping.json
```

Expected: every "Size:" line shows `$4.00 margin × 10x = $40 notional   (mult 1.0)`.

- [ ] **Step 4: Test trail SL disable**

```bash
python3 - <<'EOF'
import json
m = json.loads(open(".claude/scripts/regime_mapping.json").read())
m["trail_sl_offset_atr"] = 0.0
open(".claude/scripts/regime_mapping.json", "w").write(json.dumps(m, indent=2))
EOF
python3 .claude/scripts/punk_smart_router.py 2>&1 | grep -i "DUREX" | head -3
git checkout .claude/scripts/regime_mapping.json
```

Expected: DUREX lines show `move SL to <entry> (BE + 0.0×ATR)` (i.e. plain BE).

- [ ] **Step 5: Commit a note in findings doc**

Append to `docs/backtest_findings_2026-05-05_punk_smart_v2.md`:

```markdown
## Rollback verification

- [x] Schema v1 fallback: works
- [x] Per-veto disable: works
- [x] Sizing static disable: works
- [x] Trail SL disable: works (falls to plain BE)
```

```bash
git add docs/backtest_findings_2026-05-05_punk_smart_v2.md
git commit -m "feat(punk-smart-v2): verify rollback paths"
```

---

## Task 21: Update CLAUDE.md + finalize

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update the strategy/multi-profile section**

In `CLAUDE.md`, locate the section about `/punk-smart` (under "Comandos específicos multi-profile" or in the bitunix profile description). Add or update:

```markdown
### `/punk-smart` v2 (2026-05-05) — bitunix-only

5-stage pipeline: kill-switch → per-asset mapping → strategy → 6-veto layer
→ dynamic sizing → trail-SL annotation. Backtest 60-day, schema v2 mapping
with per-asset overrides (n≥10) + global fallback.

- Kill-switch: 2 SLs in 4h triggers PAUSE until next CR 00:00
- Vetoes: macro / blacklist / correlation / sentiment / funding / time-of-day
- Sizing: pnl_per_trade / 2.0 clipped [0.3, 1.5] × $4 margin
- Trail SL: TP1 hit → SL moves to BE + 0.2×ATR

Rollback flags in `regime_mapping.json`:
- `version: 1` → falls to v1 router behavior
- `vetos_enabled: []` → all setups bypass veto layer
- `dynamic_sizing: false` → fixed $4 margin
- `trail_sl_offset_atr: 0.0` → plain BE behavior

Daily state reset launchd: `com.wally.bitunix-daily-reset` at CR 00:00.
```

- [ ] **Step 2: Run all tests one final time**

```bash
pytest tests/punk_smart/ -v
```

Expected: 26+ tests PASS (all previously written).

- [ ] **Step 3: Confirm pre-commit hook still works**

```bash
.claude/scripts/preprompt_check.sh 2>&1 | tail -5
```

Expected: passes.

- [ ] **Step 4: Final commit**

```bash
git add CLAUDE.md
git commit -m "docs(punk-smart-v2): update CLAUDE.md with v2 pipeline"
```

- [ ] **Step 5: Verify branch is ready to merge**

```bash
git log --oneline main..HEAD
```

Should show ~21 commits, all `feat(punk-smart-v2)` or `chore/test/docs(punk-smart-v2)`.

```bash
git status
```

Expected: clean.

- [ ] **Step 6: Merge to main** (only if user gives green light)

```bash
git checkout main
git merge --no-ff feat/punk-smart-v2 -m "Merge feat/punk-smart-v2 — higher WR + lower DD pipeline"
```

---

## Self-Review

**Spec coverage check (each component → which task implements it):**

| Spec component | Task |
|---|---|
| C1. Per-asset mapping schema v2 | Task 11 |
| C1. Lookup order with fallback | Task 14 |
| C1. fetch_paginated 60-day | Task 10 |
| C2. Veto evaluator + 6 vetos | Tasks 4-8 |
| C2. Family buckets | Task 3 |
| C3. Position sizing formula | Task 9 |
| C4. asset_sl_streaks.json + blacklist | Task 1 |
| C4. sl_window.json + kill-switch | Task 2 |
| C4. open_positions reader | Task 3 |
| C4. /log-outcome hook | Task 16 |
| C4. Daily launchd reset | Task 17 |
| C5. Trail SL annotation in router | Task 15 |
| C5. Trail SL in simulate() | Task 12 |
| Validation: 60-day backtest run | Task 13 |
| Validation: OOS 70/30 | Task 18 |
| Validation: live smoke + gates | Task 19 |
| Validation: rollback paths | Task 20 |
| Definition of done: tests pass | Throughout (each task ends with pytest) |
| Definition of done: findings doc | Tasks 13, 18, 19, 20 |

All spec components covered. No gaps.

**Placeholder scan:** every step has actual code or actual commands. No "TBD", no "implement later". Task 18 has one slightly soft step ("Build train/test inputs from the 60-day backtest data") because it depends on what `backtest_split.py` actually accepts as input — that step contains explicit fallback instructions if the integration is non-trivial.

**Type consistency:**
- `VetoResult` defined Task 4 used Tasks 5, 6, 7, 8 ✓
- `state.record_sl(asset, ts, pnl_usd, memory_dir)` defined Task 1, used Tasks 2, 5, 16 with consistent args ✓
- `state.is_blacklisted(asset, now, memory_dir)` defined Task 1, used Task 5 ✓
- `state.is_kill_switch_active(now, memory_dir)` defined Task 2, used Task 14 ✓
- `state.bucket_of`, `state.open_positions` defined Task 3, used Tasks 5, 8 ✓
- `rc.compute(pnl_per_trade, base_margin, dynamic)` defined Task 9, used Task 15 ✓
- `vetos.evaluate(setup, ctx)` defined Task 8, used Task 15 ✓
- `vetos.is_approved(results)` defined Task 8, used Task 15 ✓
- `lookup_regime_info(mapping, asset, regime)` defined Task 14, used Task 14 ✓

All names and signatures internally consistent.
