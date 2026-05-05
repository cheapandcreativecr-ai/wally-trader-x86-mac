#!/usr/bin/env python3
"""punk_smart_vetos — 6 veto functions for /punk-smart v2.

Each veto: (setup, ctx) → VetoResult(passed: bool, reason: str, source: str).
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import punk_smart_state as state

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


def veto_blacklist(setup: dict, now, memory_dir=None) -> VetoResult:
    asset = setup["asset"]
    if state.is_blacklisted(asset, now, memory_dir=memory_dir):
        return VetoResult("blacklist", False,
                          f"{asset} blacklisted (2 SL streak)",
                          source="asset_sl_streaks.json")
    return VetoResult("blacklist", True, "clean", source="asset_sl_streaks.json")


_FNG_CACHE: dict = {"value": None, "fetched_at": 0}
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
