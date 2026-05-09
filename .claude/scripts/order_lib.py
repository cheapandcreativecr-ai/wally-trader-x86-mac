"""Order construction + persistence helpers called from /order slash command."""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from pending_lib import append_pending, load_all_pendings, apply_whitelist_matrix

_SCRIPTS_DIR = Path(__file__).parent


def check_cooldown(profile: str) -> tuple[bool, str]:
    """Return (blocked, reason). Calls tilt_check.py --check-cooldown-only.

    exit code 2 = cooldown active (BLOCK).
    exit code 0 = no cooldown (OK).
    Non-zero != 2 = tool error → do NOT block (fail open).
    """
    try:
        result = subprocess.run(
            [
                "python3",
                str(_SCRIPTS_DIR / "tilt_check.py"),
                "--profile", profile,
                "--check-cooldown-only",
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 2:
            try:
                data = json.loads(result.stdout)
                reason = data.get("reason") or "cooldown active"
                mins = data.get("minutes_remaining", "?")
                return True, f"cooldown_active: {mins} min remaining ({reason})"
            except Exception:
                return True, "cooldown_active (could not parse details)"
        return False, "ok"
    except Exception as exc:
        # Tool error → fail open, don't block order
        return False, f"cooldown_check_error: {exc}"


# Default TP splits per profile
DEFAULT_TP_SPLITS = {
    "retail": [0.4, 0.4, 0.2],
    "retail-bingx": [0.4, 0.4, 0.2],
    "ftmo": [0.5, 0.5],  # (handled by legacy flow anyway)
    "fotmarkets": [1.0],  # single TP at 2R
}

DEFAULT_REQUIRED_FILTERS = {
    "retail": [
        "price_touches_donchian_low_15_for_long",
        "rsi_15m_lt_35_for_long",
        "bb_lower_touch_for_long",
        "candle_close_green_for_long",
    ],
    "retail-bingx": [
        "price_touches_donchian_low_15_for_long",
        "rsi_15m_lt_35_for_long",
        "bb_lower_touch_for_long",
        "candle_close_green_for_long",
    ],
    "fotmarkets": [
        "price_touches_structural_level",
        "rsi_5m_lt_30_for_long",
        "bb_lower_touch_for_long",
        "reversal_candle_5m",
    ],
}


def _gen_id(profile: str, asset: str, side: str) -> str:
    now = datetime.now().astimezone()
    asset_slug = asset.lower().replace(".", "").replace("/", "")
    return f"ord_{now.strftime('%Y%m%d_%H%M%S')}_{profile}_{asset_slug}_{side.lower()}"


def build_order(
    profile: str,
    asset: str,
    side: str,
    entry: float,
    sl: float,
    tp1: float,
    tp2: float | None = None,
    tp3: float | None = None,
    qty: float = 0.0,
    leverage: int = 10,
    risk_usd: float = 0.0,
    risk_pct: float = 2.0,
    invalidation_price: float = 0.0,
    invalidation_side: str = "below",
    ttl_hours: float = 6.0,
    force_exit_mx: str | None = None,
    strategy: str = "mean_reversion_15m",
    check_regime_change: bool = False,
    filters_at_creation: dict | None = None,
) -> dict:
    """Construct the full order dict per spec schema."""
    side = side.upper()
    now = datetime.now().astimezone()
    expires_at = (now + timedelta(hours=ttl_hours)).isoformat(timespec="seconds")
    if force_exit_mx is None:
        # End of today at 23:59 CR (UTC-6)
        mx_now = datetime.now(timezone.utc) - timedelta(hours=6)
        mx_eod = mx_now.replace(hour=23, minute=59, second=0, microsecond=0)
        force_exit_mx = mx_eod.isoformat(timespec="seconds")

    tp_splits = DEFAULT_TP_SPLITS.get(profile, [1.0])
    tps: list[float] = [t for t in (tp1, tp2, tp3) if t is not None]
    # ensure splits and tps match
    if len(tp_splits) > len(tps):
        tp_splits = tp_splits[: len(tps)]

    order = {
        "id": _gen_id(profile, asset, side),
        "profile": profile,
        "asset": asset,
        "side": side,
        "strategy": strategy,
        "entry_type": "limit",
        "entry": entry,
        "entry_tolerance_pct": 0.1,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "tp_splits": tp_splits,
        "risk_usd": risk_usd,
        "risk_pct": risk_pct,
        "qty": qty,
        "leverage": leverage,
        "filters_at_creation": filters_at_creation or {},
        "required_filters_at_trigger": DEFAULT_REQUIRED_FILTERS.get(profile, []),
        "invalidation_price": invalidation_price,
        "invalidation_side": invalidation_side,
        "invalidation_close_tf": "4h",
        "check_regime_change": check_regime_change,
        "created_at": now.isoformat(timespec="seconds"),
        "expires_at": expires_at,
        "force_exit_mx": force_exit_mx,
        "real_order": {
            "enabled": False,
            "binance_order_id": None,
            "placed_at": None,
        },
        "status": "pending",
        "next_recheck_suggested_mx": "",
    }
    return order


def preflight_whitelist(order: dict) -> tuple[bool, str]:
    """Check if this order would be suspended by the matrix. Returns (ok, reason)."""
    all_pendings = load_all_pendings()
    # add candidate virtually
    all_pendings.setdefault(order["profile"], [])
    virtual = list(all_pendings[order["profile"]]) + [order]
    virtual_map = {**all_pendings, order["profile"]: virtual}
    active, suspended = apply_whitelist_matrix(virtual_map)
    would_suspend = any(o["id"] == order["id"] for o in suspended)
    if would_suspend:
        existing_ids = [o["id"] for o in active]
        return False, f"Would conflict with: {existing_ids}"
    return True, "ok"


def create_and_persist(order: dict) -> dict:
    """Append to pending_orders.json + return the persisted order.

    Wire-ins (v2):
    1. Cooldown gate: if tilt_check reports active cooldown → raise RuntimeError (BLOCK).
    2. Auto SL/TP: if sl is falsy (0 or None) and entry+side are available, attempt
       to compute SL via auto_sl_tp.py. Failure is non-blocking (falls through).
    """
    profile = order.get("profile", "unknown")

    # --- Gate 1: cooldown check ---
    blocked, reason = check_cooldown(profile)
    if blocked:
        raise RuntimeError(f"ORDER_BLOCKED — {reason}. Clear cooldown or use override.")

    # --- Gate 2: auto SL/TP if SL missing ---
    if not order.get("sl"):
        entry = order.get("entry")
        side = order.get("side")
        if entry and side:
            try:
                # Use a default ATR of 0.5% (rough placeholder when no live data)
                atr_pct = 0.5
                result = subprocess.run(
                    [
                        "python3",
                        str(_SCRIPTS_DIR / "auto_sl_tp.py"),
                        "--entry", str(entry),
                        "--side", str(side).upper(),
                        "--atr-pct", str(atr_pct),
                        "--regime", "RANGE_CHOP",
                        "--json",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    order["sl"] = data.get("sl_price", order.get("sl"))
                    tps = data.get("tp_levels", {})
                    if not order.get("tp1") and tps.get("tp1"):
                        order["tp1"] = tps["tp1"]
                    if not order.get("tp2") and tps.get("tp2"):
                        order["tp2"] = tps["tp2"]
                    if not order.get("tp3") and tps.get("tp3"):
                        order["tp3"] = tps["tp3"]
                    order["_auto_sl_tp_applied"] = True
            except Exception:
                pass  # fail open — let caller decide

    return append_pending(order["profile"], order)


def sizing_for_profile(profile: str, entry: float, sl: float, capital: float) -> dict:
    """Return {qty, risk_usd, risk_pct, leverage} per profile rules.

    retail/retail-bingx: 2% of capital, 10x leverage, qty = risk / sl_distance
    fotmarkets: phase-aware (Phase 1 = 10% cap $3; Phase 2 = 5%; Phase 3 = 2%)
    """
    sl_distance = abs(entry - sl)
    if sl_distance == 0:
        raise ValueError("SL distance is zero")

    if profile in ("retail", "retail-bingx"):
        risk_pct = 2.0
        leverage = 10
        risk_usd = capital * risk_pct / 100
        # qty approx: risk_usd / sl_distance (BTC perp units)
        qty = round(risk_usd / sl_distance, 6)
        return {"qty": qty, "risk_usd": round(risk_usd, 2),
                "risk_pct": risk_pct, "leverage": leverage}

    if profile == "fotmarkets":
        # Phase detection: capital < $100 → Phase 1
        if capital < 100:
            risk_pct, cap = 10.0, 3.0
        elif capital < 300:
            risk_pct, cap = 5.0, float("inf")
        else:
            risk_pct, cap = 2.0, float("inf")
        risk_usd = min(capital * risk_pct / 100, cap)
        # Fotmarkets lots — 0.01 minimum, depends on asset
        qty = 0.01  # placeholder; in practice user adjusts lot in MT5 manually
        return {"qty": qty, "risk_usd": round(risk_usd, 2),
                "risk_pct": risk_pct, "leverage": 500}

    raise ValueError(f"sizing_for_profile not implemented for {profile}")
