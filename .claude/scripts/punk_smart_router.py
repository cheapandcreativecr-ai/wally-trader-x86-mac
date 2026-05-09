#!/usr/bin/env python3
"""
punk_smart_router.py — Detecta regime + ejecuta estrategia ganadora del backtest.

Lee mapping de `regime_mapping.json` y para cada asset del watchlist:
1. Pull data (15m + 1h)
2. Clasifica regime
3. Si regime tiene strategy ganadora (PnL > 0 backtest) → ejecuta esa
4. Si regime es STAND_ASIDE (PnL <= 0) → no recomienda este asset
5. Devuelve top setups ordenados por R:R

Mapping ganador (auto-loaded):
- STRONG_TREND_UP   → A_VWAP         ✅
- RANGING           → A_VWAP         ✅
- MIXED             → A_VWAP         ✅
- SQUEEZE           → B_TrendPullback ✅
- WEAK_TREND_DOWN   → B_TrendPullback ✅
- STRONG_TREND_DOWN → STAND_ASIDE
- WEAK_TREND_UP     → STAND_ASIDE
- VOLATILE          → STAND_ASIDE (insuficiente data)
"""

import csv
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

_SHARED = Path(__file__).resolve().parent.parent.parent / "shared/wally_core/src"
if _SHARED.exists() and str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

try:
    from wally_core.portfolio import would_breach, Position
    _PORTFOLIO_AVAILABLE = True
except ImportError:
    _PORTFOLIO_AVAILABLE = False

from backtest_regime_matrix import (
    fetch, calc_atr, calc_rsi, calc_ema, calc_macd, calc_bb, calc_adx, calc_vwap,
    classify_regime, strat_a_vwap, strat_b_trending_pullback,
    strat_c_bb_squeeze_break, strat_d_momentum_macd, strat_e_range_bounce,
)
import punk_smart_state as state
import punk_smart_vetos as vetos
import regime_confidence as rc

CR_OFFSET = state.CR_OFFSET
ASSETS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "MSTRUSDT", "AVAXUSDT",
          "INJUSDT", "DOGEUSDT", "WIFUSDT", "XLMUSDT",
          "BCHUSDT", "STRKUSDT", "TONUSDT", "TRXUSDT", "PIPPINUSDT"]

STRATEGY_FNS = {
    "A_VWAP": strat_a_vwap,
    "B_TrendPullback": strat_b_trending_pullback,
    "C_BBSqueeze": strat_c_bb_squeeze_break,
    "D_MACDMomentum": strat_d_momentum_macd,
    "E_RangeBounce": strat_e_range_bounce,
}

MAPPING_FILE = Path(__file__).parent / "regime_mapping.json"
CAPITAL_USD = 200.0  # Bitunix profile capital — updated manually when profile equity changes
MAX_HEAT_PCT = 15.0   # portfolio heat limit


def _load_open_positions() -> list:
    """Load currently open (pending outcome) positions from signals_received.csv.

    Returns list of wally_core.portfolio.Position objects, or empty if unavailable.
    """
    if not _PORTFOLIO_AVAILABLE:
        return []
    profiles_dir = Path(os.environ.get("WALLY_PROFILES_DIR", ".claude/profiles"))
    csv_path = profiles_dir / "bitunix" / "memory" / "signals_received.csv"
    if not csv_path.exists():
        return []
    positions = []
    try:
        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("outcome", "pending").lower() == "pending":
                    try:
                        margin = float(row.get("margin_usd") or 50.0)
                        leverage = int(row.get("leverage") or 10)
                        entry = float(row.get("entry") or 0)
                        sl = float(row.get("sl") or 0) or None
                        symbol = row.get("symbol") or "UNKNOWN"
                        side = row.get("side", "LONG").upper()
                        if entry > 0:
                            # qty ≈ notional / entry
                            qty = round(margin * leverage / entry, 6)
                            positions.append(
                                Position(
                                    symbol=symbol,
                                    side=side,
                                    margin_usd=margin,
                                    leverage=leverage,
                                    entry_price=entry,
                                    sl_price=sl,
                                    qty=qty,
                                )
                            )
                    except (ValueError, TypeError):
                        continue
    except Exception:
        pass
    return positions


def load_mapping() -> dict:
    if not MAPPING_FILE.exists():
        print(f"❌ Mapping not found: {MAPPING_FILE}", file=sys.stderr)
        sys.exit(1)
    return json.loads(MAPPING_FILE.read_text())


def lookup_regime_info(mapping: dict, asset: str, regime: str) -> Optional[dict]:
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
                "strategy": strategy_name,
                "reason": f"strategy {strategy_name} not registered in STRATEGY_FNS"}
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


def main():
    import argparse
    p = argparse.ArgumentParser(description="Smart router — regime detection + best strategy execution")
    p.add_argument("--asset", help="Single asset (default: scan all)")
    p.add_argument("--json", action="store_true")
    p.add_argument("--show-all", action="store_true", help="Mostrar también STAND_ASIDE / NO_SETUP")
    args = p.parse_args()

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
        # Stage 6: portfolio breach guard (new v2 wire-in)
        if _PORTFOLIO_AVAILABLE:
            try:
                open_positions = _load_open_positions()
                sizing_margin = r.get("sizing", {}).get("margin_usd", 4.0)
                new_pos = Position(
                    symbol=r["asset"],
                    side=r["side"],
                    margin_usd=sizing_margin,
                    leverage=10,
                    entry_price=r["entry"],
                    sl_price=r.get("sl") or None,
                    qty=round(sizing_margin * 10 / r["entry"], 6) if r["entry"] else 0.0,
                )
                breach = would_breach(new_pos, open_positions, CAPITAL_USD, MAX_HEAT_PCT)
                if breach.breach:
                    r["status"] = "VETOED"
                    r["vetos"] = r.get("vetos", []) + [{
                        "name": "portfolio_heat",
                        "passed": False,
                        "reason": f"would_breach: {breach.reason} {breach.detail}",
                    }]
                    vetoed.append(r)
                    continue
            except Exception as exc:
                # Non-blocking — log but don't block the signal
                r["portfolio_breach_check"] = f"error: {exc}"

        r["status"] = "APPROVED"
        approved.append(r)

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


if __name__ == "__main__":
    main()
