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
    """Record an SL on `asset`. After 2 SLs, asset is blacklisted until next CR 00:00.

    Behavior on 3rd+ SL: the blacklist_until is updated to the new SL's next
    CR midnight (effectively keeping the asset blacklisted as long as SLs continue).

    The `pnl_usd` argument is accepted for API symmetry but is persisted to
    sl_window.json (kill-switch tracker), which is wired up in a follow-up task.
    """
    p = _streaks_path(memory_dir)
    data = _load(p, {"version": 1, "as_of_cr_date": None, "assets": {}})
    cell = data["assets"].get(asset, {"sl_count": 0, "last_sl_ts": None,
                                       "blacklist_until": None})
    cell["sl_count"] = cell["sl_count"] + 1
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
