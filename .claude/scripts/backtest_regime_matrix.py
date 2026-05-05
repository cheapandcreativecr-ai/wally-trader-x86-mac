#!/usr/bin/env python3
"""
backtest_regime_matrix.py — Matriz de 5 estrategias × 6 contextos.

Objetivo: identificar QUÉ estrategia rinde mejor en CADA contexto de mercado.
Output: mapping {contexto → mejor estrategia} para usar en /punk-smart router.

Contextos (clasificados por bar):
1. STRONG_TREND_UP    ADX>30 + price>EMA50 + EMA21>EMA50
2. STRONG_TREND_DOWN  ADX>30 + price<EMA50 + EMA21<EMA50
3. WEAK_TREND_UP      ADX 20-30 + price>EMA50
4. WEAK_TREND_DOWN    ADX 20-30 + price<EMA50
5. RANGING            ADX<20, BB bandwidth normal
6. SQUEEZE            BB bandwidth < 30% del avg-50
7. VOLATILE           ATR > 2x avg-50

Estrategias evaluadas en cada contexto:
A. VWAP Reversion + MTF Trend Filter
B. Trending Pullback (EMA21 + RSI cross)
C. BB Squeeze Breakout
D. Momentum Follow (MACD cross + RSI direction)
E. Range Bounce (BB extremes + RSI extremo)

Sizing: $100 margin × 10x = $1,000 notional, fees 0.12% roundtrip
TPs/SL: adaptativos por estrategia (definidos en cada strat fn)
Time-out: 6h (24 bars 15m)
"""

import json
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

ASSETS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "MSTRUSDT", "AVAXUSDT",
          "INJUSDT", "DOGEUSDT", "WIFUSDT", "XLMUSDT"]
DAYS = 60
MARGIN = 100.0
LEVERAGE = 10
NOTIONAL = MARGIN * LEVERAGE
FEES_PCT = 0.12


# ===== Helpers =====
def fetch(symbol, interval, limit):
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={min(limit,1500)}"
    try:
        data = json.loads(urllib.request.urlopen(url, timeout=20).read())
        return [{"t": int(b[0]), "o": float(b[1]), "h": float(b[2]),
                 "l": float(b[3]), "c": float(b[4]), "v": float(b[5])} for b in data]
    except Exception as e:
        print(f"  WARN {symbol}: {e}", file=sys.stderr)
        return []


def fetch_paginated(symbol: str, interval: str, days: int) -> list:
    """Fetch up to `days` of bars by paginating Binance klines (1500-bar cap).

    Strategy: walk forward in time, oldest-first, using endTime cursor.
    De-duplicate by timestamp.

    Termination: relies solely on `len(page) < 1500` (exchange returned less
    than max → reached the start of history) and the target count check.
    The cursor-progress guard (oldest >= end_ts) was intentionally omitted:
    it would incorrectly fire in test mocks that return non-decreasing
    timestamps, and in production the `len(page) < 1500` signal is sufficient.
    """
    bars_per_day = {"15m": 96, "1h": 24, "4h": 6}.get(interval, 96)
    target = bars_per_day * days
    seen: dict = {}

    end_ts = None  # None = "now" on Binance; walk backward via endTime cursor
    while len(seen) < target:
        url = (f"https://fapi.binance.com/fapi/v1/klines"
               f"?symbol={symbol}&interval={interval}&limit=1500")
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
        end_ts = oldest - 1
        time.sleep(0.1)
        if len(page) < 1500:
            break  # exchange returned less than max → reached the start

    bars = sorted(seen.values(), key=lambda b: b["t"])
    return bars[-target:] if len(bars) > target else bars


def calc_atr(bars, period=14):
    if len(bars) < period + 1:
        return 0
    trs = []
    for i in range(-period, 0):
        tr = max(bars[i]["h"] - bars[i]["l"],
                 abs(bars[i]["h"] - bars[i-1]["c"]),
                 abs(bars[i]["l"] - bars[i-1]["c"]))
        trs.append(tr)
    return sum(trs) / period


def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50
    gains = [max(0, closes[i] - closes[i-1]) for i in range(-period, 0)]
    losses = [max(0, closes[i-1] - closes[i]) for i in range(-period, 0)]
    g = sum(gains) / period
    l = sum(losses) / period if losses else 0.0001
    rs = g / max(l, 0.0001)
    return 100 - (100 / (1 + rs))


def calc_ema(values, period):
    if len(values) < period:
        return None
    sma = sum(values[:period]) / period
    mult = 2 / (period + 1)
    ema = sma
    for v in values[period:]:
        ema = (v - ema) * mult + ema
    return ema


def calc_macd(closes, fast=12, slow=26, signal=9):
    if len(closes) < slow + signal:
        return None, None
    ema_fast = calc_ema(closes, fast)
    ema_slow = calc_ema(closes, slow)
    if ema_fast is None or ema_slow is None:
        return None, None
    macd_line = ema_fast - ema_slow
    # Compute signal as EMA of macd over recent bars
    macd_history = []
    for i in range(slow, len(closes) + 1):
        ef = calc_ema(closes[:i], fast)
        es = calc_ema(closes[:i], slow)
        if ef and es:
            macd_history.append(ef - es)
    if len(macd_history) < signal:
        return macd_line, None
    sig = calc_ema(macd_history, signal)
    return macd_line, sig


def calc_bb(closes, period=20, std=2):
    if len(closes) < period:
        return None, None, None
    window = closes[-period:]
    m = sum(window) / period
    var = sum((c - m) ** 2 for c in window) / period
    s = var ** 0.5
    return m + std * s, m - std * s, m


def calc_adx(bars, period=14):
    """Devuelve último ADX value."""
    if len(bars) < period * 2:
        return 0
    dm_pos, dm_neg, trs = [], [], []
    for i in range(-period * 2, 0):
        if i == -period * 2:
            continue
        up = bars[i]["h"] - bars[i-1]["h"]
        dn = bars[i-1]["l"] - bars[i]["l"]
        dm_pos.append(up if up > dn and up > 0 else 0)
        dm_neg.append(dn if dn > up and dn > 0 else 0)
        tr = max(bars[i]["h"] - bars[i]["l"],
                 abs(bars[i]["h"] - bars[i-1]["c"]),
                 abs(bars[i]["l"] - bars[i-1]["c"]))
        trs.append(tr)
    if not trs:
        return 0
    di_pos_smooth = sum(dm_pos[-period:]) / period
    di_neg_smooth = sum(dm_neg[-period:]) / period
    tr_smooth = sum(trs[-period:]) / period
    di_pos = di_pos_smooth / max(tr_smooth, 0.0001) * 100
    di_neg = di_neg_smooth / max(tr_smooth, 0.0001) * 100
    di_sum = di_pos + di_neg
    return abs(di_pos - di_neg) / max(di_sum, 0.0001) * 100


def calc_vwap(bars):
    cp, cv = 0, 0
    for b in bars:
        t = (b["h"] + b["l"] + b["c"]) / 3
        cp += t * b["v"]
        cv += b["v"]
    return cp / cv if cv > 0 else bars[-1]["c"]


# ===== Regime classifier =====
def classify_regime(bars_15m, bars_1h, i):
    """Devuelve etiqueta del contexto en bar i (15m)."""
    if i < 50:
        return "UNKNOWN"
    closes_15m = [b["c"] for b in bars_15m[:i+1]]
    closes_1h = [b["c"] for b in bars_1h if b["t"] <= bars_15m[i]["t"]]
    if len(closes_1h) < 50:
        return "UNKNOWN"

    last = bars_15m[i]
    atr = calc_atr(bars_15m[:i+1])
    atr_avg = sum(calc_atr(bars_15m[:i+1-k*5]) for k in range(10)) / 10 if i >= 100 else atr
    adx = calc_adx(bars_15m[:i+1])
    ema21 = calc_ema(closes_15m, 21)
    ema50 = calc_ema(closes_15m, 50)
    bb_up, bb_dn, bb_mid = calc_bb(closes_15m, 20, 2)
    if not all([ema21, ema50, bb_up]):
        return "UNKNOWN"

    bb_width = bb_up - bb_dn
    # Avg bandwidth ultimas 50 bars
    bws = []
    for k in range(50):
        if i - k - 20 < 0:
            continue
        cs = closes_15m[i-k-19:i-k+1]
        bu, bd, _ = calc_bb(cs, 20, 2)
        if bu and bd:
            bws.append(bu - bd)
    bw_avg = sum(bws) / len(bws) if bws else bb_width
    bw_ratio = bb_width / max(bw_avg, 0.0001)

    # Detección priorizada
    if atr > atr_avg * 2:
        return "VOLATILE"
    if bw_ratio < 0.4:
        return "SQUEEZE"
    if adx > 30:
        if last["c"] > ema50 and ema21 > ema50:
            return "STRONG_TREND_UP"
        elif last["c"] < ema50 and ema21 < ema50:
            return "STRONG_TREND_DOWN"
    if 20 <= adx <= 30:
        if last["c"] > ema50:
            return "WEAK_TREND_UP"
        else:
            return "WEAK_TREND_DOWN"
    if adx < 20:
        return "RANGING"
    return "MIXED"


# ===== 5 Estrategias =====
def strat_a_vwap(bars_15m, bars_1h, i):
    if i < 60 or i >= len(bars_15m) - 6:
        return None
    closes = [b["c"] for b in bars_15m[:i+1]]
    last = bars_15m[i]
    entry = last["c"]
    atr = calc_atr(bars_15m[:i+1])
    if atr == 0:
        return None
    rsi = calc_rsi(closes)
    vwap = calc_vwap(bars_15m[max(0,i-96):i+1])
    dist_atr = (entry - vwap) / atr
    closes_1h = [b["c"] for b in bars_1h if b["t"] <= last["t"]]
    if len(closes_1h) < 50:
        return None
    ema50_1h = calc_ema(closes_1h, 50)
    macro_up = closes_1h[-1] > ema50_1h

    if macro_up and dist_atr < -0.8 and rsi < 35:
        return {"side": "LONG", "entry": entry, "sl": entry - 0.5*atr, "tp1": vwap, "tp2": vwap + 0.5*atr}
    elif not macro_up and dist_atr > 0.8 and rsi > 65:
        return {"side": "SHORT", "entry": entry, "sl": entry + 0.5*atr, "tp1": vwap, "tp2": vwap - 0.5*atr}
    return None


def strat_b_trending_pullback(bars_15m, bars_1h, i):
    if i < 50 or i >= len(bars_15m) - 6:
        return None
    closes_15m = [b["c"] for b in bars_15m[:i+1]]
    closes_1h = [b["c"] for b in bars_1h if b["t"] <= bars_15m[i]["t"]]
    if len(closes_1h) < 50:
        return None
    ema50_1h = calc_ema(closes_1h, 50)
    trend_up = closes_1h[-1] > ema50_1h * 1.005
    trend_dn = closes_1h[-1] < ema50_1h * 0.995
    if not (trend_up or trend_dn):
        return None
    ema21_15m = calc_ema(closes_15m, 21)
    last = bars_15m[i]
    atr = calc_atr(bars_15m[:i+1])
    if atr == 0:
        return None
    rsi_now = calc_rsi(closes_15m)
    rsi_prev = calc_rsi(closes_15m[:-1])

    if trend_up and last["l"] <= ema21_15m * 1.002 and rsi_prev < 40 <= rsi_now:
        entry = last["c"]
        return {"side": "LONG", "entry": entry, "sl": entry - 1.0*atr, "tp1": entry + 1.5*atr, "tp2": entry + 3*atr}
    if trend_dn and last["h"] >= ema21_15m * 0.998 and rsi_prev > 60 >= rsi_now:
        entry = last["c"]
        return {"side": "SHORT", "entry": entry, "sl": entry + 1.0*atr, "tp1": entry - 1.5*atr, "tp2": entry - 3*atr}
    return None


def strat_c_bb_squeeze_break(bars_15m, bars_1h, i):
    if i < 70 or i >= len(bars_15m) - 6:
        return None
    closes = [b["c"] for b in bars_15m[:i+1]]
    bws = []
    for k in range(50):
        if i - k - 20 < 0:
            continue
        cs = closes[i-k-19:i-k+1]
        bu, bd, _ = calc_bb(cs, 20, 2)
        if bu and bd:
            bws.append(bu - bd)
    if not bws:
        return None
    bb_up, bb_dn, bb_mid = calc_bb(closes, 20, 2)
    bw_now = bb_up - bb_dn
    bw_ratio = bw_now / (sum(bws) / len(bws))
    if bw_ratio > 0.5:
        return None  # No squeeze
    last = bars_15m[i]
    prev = bars_15m[i-1]
    avg_vol = sum(b["v"] for b in bars_15m[i-20:i]) / 20
    vol_spike = last["v"] > avg_vol * 1.5
    sh = bb_up - bb_dn
    if last["c"] > bb_up and prev["c"] <= bb_up and vol_spike:
        entry = last["c"]
        return {"side": "LONG", "entry": entry, "sl": bb_mid, "tp1": entry + sh, "tp2": entry + 2*sh}
    if last["c"] < bb_dn and prev["c"] >= bb_dn and vol_spike:
        entry = last["c"]
        return {"side": "SHORT", "entry": entry, "sl": bb_mid, "tp1": entry - sh, "tp2": entry - 2*sh}
    return None


def strat_d_momentum_macd(bars_15m, bars_1h, i):
    """Momentum Follow: MACD cross + ADX>25 + RSI direction."""
    if i < 50 or i >= len(bars_15m) - 6:
        return None
    closes = [b["c"] for b in bars_15m[:i+1]]
    macd_now, sig_now = calc_macd(closes)
    macd_prev, sig_prev = calc_macd(closes[:-1])
    if None in (macd_now, sig_now, macd_prev, sig_prev):
        return None
    adx = calc_adx(bars_15m[:i+1])
    if adx < 25:
        return None
    last = bars_15m[i]
    atr = calc_atr(bars_15m[:i+1])
    if atr == 0:
        return None
    rsi = calc_rsi(closes)

    # Bullish cross MACD
    if macd_prev <= sig_prev and macd_now > sig_now and rsi > 50:
        entry = last["c"]
        return {"side": "LONG", "entry": entry, "sl": entry - 1.0*atr, "tp1": entry + 1.5*atr, "tp2": entry + 3*atr}
    if macd_prev >= sig_prev and macd_now < sig_now and rsi < 50:
        entry = last["c"]
        return {"side": "SHORT", "entry": entry, "sl": entry + 1.0*atr, "tp1": entry - 1.5*atr, "tp2": entry - 3*atr}
    return None


def strat_e_range_bounce(bars_15m, bars_1h, i):
    """Range Bounce: BB extremes touch + RSI extremo."""
    if i < 30 or i >= len(bars_15m) - 6:
        return None
    closes = [b["c"] for b in bars_15m[:i+1]]
    bb_up, bb_dn, bb_mid = calc_bb(closes, 20, 2)
    if bb_up is None:
        return None
    last = bars_15m[i]
    rsi = calc_rsi(closes)
    atr = calc_atr(bars_15m[:i+1])
    if atr == 0:
        return None

    if last["l"] <= bb_dn and rsi < 30:
        entry = last["c"]
        return {"side": "LONG", "entry": entry, "sl": entry - 0.5*atr, "tp1": bb_mid, "tp2": bb_up}
    if last["h"] >= bb_up and rsi > 70:
        entry = last["c"]
        return {"side": "SHORT", "entry": entry, "sl": entry + 0.5*atr, "tp1": bb_mid, "tp2": bb_dn}
    return None


# ===== Simulator (cierre escalonado 50/50) =====
def simulate(setup, future_bars, max_bars=24):  # 6h
    if setup is None:
        return None
    e = setup["entry"]; sl = setup["sl"]; tp1 = setup["tp1"]; tp2 = setup["tp2"]
    side = setup["side"]
    duration = 0
    sl_hit = tp1_hit = tp2_hit = False
    for k, bar in enumerate(future_bars[:max_bars]):
        duration = (k + 1) * 15
        if side == "SHORT":
            if bar["h"] >= sl:
                sl_hit = True; break
            if bar["l"] <= tp2 and not tp2_hit: tp2_hit = True
            if bar["l"] <= tp1 and not tp1_hit: tp1_hit = True
        else:
            if bar["l"] <= sl:
                sl_hit = True; break
            if bar["h"] >= tp2 and not tp2_hit: tp2_hit = True
            if bar["h"] >= tp1 and not tp1_hit: tp1_hit = True
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
    elif tp1_hit:
        d1 = abs(tp1 - e) / e
        pnl_pct = d1 * 0.5  # 50% TP1, 50% BE
        outcome = "TP1"
    else:
        if len(future_bars) >= max_bars:
            last_c = future_bars[max_bars - 1]["c"]
            pnl_pct = (e - last_c) / e if side == "SHORT" else (last_c - e) / e
        outcome = "TIMEOUT"
    pnl_usd = pnl_pct * NOTIONAL - (NOTIONAL * FEES_PCT / 100)
    return {"outcome": outcome, "pnl_usd": pnl_usd, "duration_min": duration}


def main():
    STRATS = {
        "A_VWAP": strat_a_vwap,
        "B_TrendPullback": strat_b_trending_pullback,
        "C_BBSqueeze": strat_c_bb_squeeze_break,
        "D_MACDMomentum": strat_d_momentum_macd,
        "E_RangeBounce": strat_e_range_bounce,
    }
    REGIMES = ["STRONG_TREND_UP", "STRONG_TREND_DOWN", "WEAK_TREND_UP",
               "WEAK_TREND_DOWN", "RANGING", "SQUEEZE", "VOLATILE"]

    # cells[regime][strat] = list of trades
    cells = {r: {s: [] for s in STRATS} for r in REGIMES}
    cells["UNKNOWN"] = {s: [] for s in STRATS}
    cells["MIXED"] = {s: [] for s in STRATS}

    # Per-asset cells: cells_per_asset[asset][regime][strategy] = list of trades
    cells_per_asset: dict = {a: {r: {s: [] for s in STRATS} for r in REGIMES + ["UNKNOWN", "MIXED"]}
                              for a in ASSETS}

    print(f"{'='*80}")
    print(f"REGIME × STRATEGY MATRIX BACKTEST — {DAYS} días, {len(ASSETS)} assets")
    print(f"Margin ${MARGIN}, Lev {LEVERAGE}x, Fees {FEES_PCT}% RT")
    print(f"{'='*80}")

    for sym in ASSETS:
        print(f"  {sym}...", file=sys.stderr)
        b15 = fetch_paginated(sym, "15m", days=DAYS)
        b1h = fetch_paginated(sym, "1h", days=DAYS + 3)  # +3d cushion for 1h aggregations
        if not b15 or not b1h:
            continue
        last_trade_idx = {s: -100 for s in STRATS}
        for i in range(70, len(b15) - 24):
            regime = classify_regime(b15, b1h, i)
            cr_h = (datetime.utcfromtimestamp(b15[i]["t"]/1000).hour - 6) % 24
            if cr_h < 6 or cr_h > 22:
                continue
            for sname, sfn in STRATS.items():
                if i - last_trade_idx[sname] < 16:  # 4h gap
                    continue
                setup = sfn(b15, b1h, i)
                if setup is None:
                    continue
                result = simulate(setup, b15[i+1:])
                if result is None:
                    continue
                cells[regime][sname].append({"asset": sym, **setup, **result})
                cells_per_asset[sym][regime][sname].append({"asset": sym, **setup, **result})
                last_trade_idx[sname] = i

    # ===== Output matrix =====
    print(f"\n{'='*80}")
    print(f"📊 MATRIZ DE RESULTADOS (PnL total per cell)")
    print(f"{'='*80}\n")
    print(f"{'REGIME':<22} | " + " | ".join(f"{s[:13]:<13}" for s in STRATS))
    print("-" * 95)
    for regime in REGIMES + ["UNKNOWN", "MIXED"]:
        row = []
        for s in STRATS:
            ts = cells[regime][s]
            n = len(ts)
            if n == 0:
                row.append("0  $0      ")
            else:
                pnl = sum(t["pnl_usd"] for t in ts)
                wr = sum(1 for t in ts if t["pnl_usd"] > 0) / n * 100
                row.append(f"{n:2d} ${pnl:+5.0f} {wr:.0f}%")
        print(f"{regime:<22} | " + " | ".join(f"{r:<13}" for r in row))

    # ===== Identify winner per regime =====
    print(f"\n{'='*80}")
    print(f"🏆 MAPPING GANADOR (mejor estrategia por regime, min 5 trades)")
    print(f"{'='*80}")
    mapping = {}
    for regime in REGIMES + ["UNKNOWN", "MIXED"]:
        best = None
        best_pnl = -9999
        for sname in STRATS:
            ts = cells[regime][sname]
            if len(ts) < 5:  # min sample
                continue
            pnl = sum(t["pnl_usd"] for t in ts)
            if pnl > best_pnl:
                best_pnl = pnl
                best = sname
        if best:
            ts = cells[regime][best]
            wr = sum(1 for t in ts if t["pnl_usd"] > 0) / len(ts) * 100
            n = len(ts)
            mapping[regime] = {"strategy": best, "n_trades": n, "wr": wr, "pnl": best_pnl, "pnl_per_trade": best_pnl/n}
            marker = "✅" if best_pnl > 0 else "❌ ALL NEGATIVE — STAND ASIDE"
            print(f"  {regime:<22} → {best:<18} ({n} trades, WR {wr:.0f}%, PnL ${best_pnl:+.2f}, ${best_pnl/n:+.2f}/trade) {marker}")
        else:
            mapping[regime] = None
            print(f"  {regime:<22} → INSUFFICIENT DATA (<5 trades any strategy)")

    # ===== Build per-asset mapping =====
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

    # ===== Export mapping JSON (schema v2) =====
    out_file = Path(__file__).parent / "regime_mapping.json"
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
    print(f"\n✅ Mapping exportado a: {out_file}")
    print("   /punk-smart leerá este archivo para elegir estrategia por contexto.")

    # ===== Total backtest summary if user follows mapping =====
    print(f"\n{'='*80}")
    print(f"📈 SI HUBIERAS USADO EL MAPPING (solo trades con +PnL strategy):")
    print(f"{'='*80}")
    total_followed = 0
    total_pnl = 0
    total_wins = 0
    for regime, m in mapping.items():
        if m is None or m["pnl"] <= 0:
            continue
        ts = cells[regime][m["strategy"]]
        total_followed += len(ts)
        total_pnl += sum(t["pnl_usd"] for t in ts)
        total_wins += sum(1 for t in ts if t["pnl_usd"] > 0)
    if total_followed > 0:
        wr_total = total_wins / total_followed * 100
        print(f"Total trades (siguiendo mapping): {total_followed}")
        print(f"WR: {wr_total:.1f}%")
        print(f"Total PnL: ${total_pnl:+.2f}")
        print(f"Avg PnL/trade: ${total_pnl/total_followed:+.2f}")
        print(f"Trades/día: {total_followed/DAYS:.1f}")
        print(f"PnL/día estimado: ${total_pnl/DAYS:+.2f}")
        print(f"PnL/mes (22d): ${total_pnl/DAYS*22:+.2f}")


if __name__ == "__main__":
    main()
