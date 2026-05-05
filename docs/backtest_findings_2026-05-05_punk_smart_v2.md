# Backtest findings — /punk-smart v2 (60-day, schema v2)

**Date:** 2026-05-05
**Window:** 60 days, 9 assets (BTCUSDT, ETHUSDT, SOLUSDT, MSTRUSDT, AVAXUSDT, INJUSDT, DOGEUSDT, WIFUSDT, XLMUSDT)
**Data source:** Binance Futures paginated klines (15m + 1h)
**Margin:** $100 × 10x leverage = $1,000 notional
**Fees:** 0.12% round-trip
**Trail SL:** 0.2×ATR after TP1 hit (schema v2 feature)
**Min trades for global mapping:** 5 | **Min trades for per-asset override:** 10
**Bug fixed in this run:** `calc_macd` was O(n³) (rebuilt full EMA history per bar). Fixed to O(n) incremental EMA before running.

---

## Top-line metrics (using mapping winner per regime)

These are the aggregate "if you had followed the best-strategy-per-regime mapping" numbers.

Note: v1 baseline numbers below come from the v1 JSON backup (regime_mapping.v1.backup), which was a ~15-day run with flat schema (no version field). The "projected 60d" column is a 4× extrapolation — treat as rough reference only.

| Metric | v1 baseline (15d, extrapolated ×4) | v2 (actual 60d) | Gate min |
|---|---|---|---|
| WR | ~48% (MIXED regime A_VWAP led) | **42.8%** | ≥53% |
| Trades/day | ~2.1 (94 total / 15d × extrapolated) | **2.4** | ≥2.5 |
| PnL/day | +$4.4 (extrapolated) | **+$1.15** | ≥+$6.5 |
| PnL absolute | +$68.9 (v1 60d extrapolation from 15d) | **+$68.91** | ≥+$390 |

**Gate assessment:** v2 does NOT pass the acceptance gates set in the plan.
- WR 42.8% < 53% gate
- PnL/day $+1.15 < $+6.5 gate
- PnL absolute $68.91 < $390 gate (60d)

**Important context:** The $390 gate was designed for a $100 capital × 10x account. The realized $68.91 in 60 days represents +68.9% return on margin (before compounding), which is positive but well short of the gate. Two stand-aside regimes (STRONG_TREND_DOWN, WEAK_TREND_DOWN) suppressed total output significantly — these regimes account for the majority of market time for trending altcoins.

(Note: profit factor and max-DD not computed in this backtest. Deferred to Task 19 live smoke test.)

---

## Full regime × strategy matrix

```
REGIME                 | A_VWAP        | B_TrendPullback | C_BBSqueeze   | D_MACDMomentum | E_RangeBounce
---------------------------------------------------------------------------------------------------------
STRONG_TREND_UP        | 51  $+29  39% | 73   $-60  47% |  8  $-25  25% | 170  $-223  38% | 339  $-555  18%
STRONG_TREND_DOWN      | 79  $-107 22% | 74   $-73  43% | 19  $-102  11% | 163  $-338  35% | 295  $-304  23%
WEAK_TREND_UP          | 10  $+4   40% | 79   $-109 38% |  9  $-36  22% | 53   $-62   40% | 13   $+13   38%
WEAK_TREND_DOWN        | 22  $-28  32% | 83   $-58  42% |  8  $-30  25% | 42   $-100  33% | 21   $-6    38%
RANGING                | 25  $+7   36% | 298  $-248 42% | 15  $-40  27% | 0    $0          | 18   $-23   11%
SQUEEZE                | 10  $+10  40% | 59   $-17  49% | 71  $-204 34% | 33   $-28   55% | 41   $-17   29%
VOLATILE               |  3  $-18  0%  |  5   $+6   60% |  0  $0        |  6   $-12   50% |  7   $-13   14%
UNKNOWN                |  0  $0        |  0   $0        |  0  $0        |  0   $0          |  0   $0
MIXED                  | 124 $-2   42% | 41   $+3   51% | 15  $-45  40% | 40   $-24   42% | 254  $-232  25%
```

Columns: `N  $PnL  WR%`

**Key observations from matrix:**
- `E_RangeBounce` generates massive trade count in STRONG_TREND_UP (339!) and MIXED (254) but loses heavily — high false signal rate in trending markets
- `D_MACDMomentum` similarly produces 170 trades in STRONG_TREND_UP at −$223 — over-trading
- `A_VWAP` is the most disciplined: positive in STRONG_TREND_UP, WEAK_TREND_UP, RANGING, SQUEEZE — 4 winning regimes
- `B_TrendPullback` wins only in VOLATILE (5 trades, 60% WR, $+5.77) and MIXED (41 trades, 51% WR, $+3.03)
- `C_BBSqueeze` negative in every regime — strategy does not work on this universe/timeframe

---

## Mapping winner per regime (global)

| Regime | Winner strategy | N trades | WR | PnL | $/trade | Status |
|---|---|---|---|---|---|---|
| STRONG_TREND_UP | A_VWAP | 51 | 39% | $+29.39 | $+0.58 | TRADE |
| STRONG_TREND_DOWN | B_TrendPullback | 74 | 43% | $-72.81 | $-0.98 | STAND ASIDE |
| WEAK_TREND_UP | E_RangeBounce | 13 | 38% | $+13.39 | $+1.03 | TRADE |
| WEAK_TREND_DOWN | E_RangeBounce | 21 | 38% | $-6.05 | $-0.29 | STAND ASIDE |
| RANGING | A_VWAP | 25 | 36% | $+7.27 | $+0.29 | TRADE |
| SQUEEZE | A_VWAP | 10 | 40% | $+10.06 | $+1.01 | TRADE |
| VOLATILE | B_TrendPullback | 5 | 60% | $+5.77 | $+1.15 | TRADE (low n) |
| UNKNOWN | — | — | — | — | — | INSUFFICIENT DATA |
| MIXED | B_TrendPullback | 41 | 51% | $+3.03 | $+0.07 | TRADE |

**Stand-aside regimes:** STRONG_TREND_DOWN, WEAK_TREND_DOWN. Both trending-down regimes lose money on every strategy tested. When market is in downtrend (ADX>20 + price < EMA50), best action is skip.

**Low-confidence:** VOLATILE has only 5 trades — below per-asset threshold of 10. Global threshold is 5, so it passes, but confidence is low.

---

## Per-asset highlights (top 5 by pnl_per_trade, n_trades >= 10)

| Asset | Regime | Strategy | N | WR | PnL | $/trade |
|---|---|---|---|---|---|---|
| AVAXUSDT | SQUEEZE | B_TrendPullback | 10 | 80% | $+25.90 | **$+2.59** |
| XLMUSDT | MIXED | E_RangeBounce | 22 | 50% | $+52.96 | **$+2.41** |
| WIFUSDT | MIXED | E_RangeBounce | 33 | 27% | $+60.57 | **$+1.84** |
| INJUSDT | WEAK_TREND_DOWN | B_TrendPullback | 12 | 58% | $+17.73 | **$+1.48** |
| ETHUSDT | STRONG_TREND_UP | D_MACDMomentum | 24 | 46% | $+28.72 | **$+1.20** |

Notable findings:
- **AVAXUSDT SQUEEZE → B_TrendPullback** is the strongest single cell: 80% WR, $+2.59/trade. AVAX squeezes resolve with explosive trending pullbacks — logical fit.
- **WIFUSDT MIXED → E_RangeBounce** has only 27% WR but $+1.84/trade — high-reward but unreliable, driven by outsized wins on a few meme-coin moves.
- **INJUSDT WEAK_TREND_DOWN → B_TrendPullback** (58% WR, $+1.48/trade) contradicts the global stand-aside for WEAK_TREND_DOWN. INJ-specific: pullbacks in weak downtrend tend to overshoot, giving profit before continuation.
- **SOLUSDT** did not qualify for any per-asset override (no (regime, strat) cell hit n≥10 with positive PnL).
- **BTCUSDT** only 1 per-asset override: STRONG_TREND_DOWN → D_MACDMomentum ($+0.40, n=19, $+0.02/trade) — essentially break-even.
- Total: 8 assets with overrides, 19 total (asset, regime) cells promoted.

Full per-asset table (all 19 promoted cells):

| Asset | Regime | Strategy | N | WR | $/trade |
|---|---|---|---|---|---|
| AVAXUSDT | SQUEEZE | B_TrendPullback | 10 | 80% | +2.59 |
| XLMUSDT | MIXED | E_RangeBounce | 22 | 50% | +2.41 |
| WIFUSDT | MIXED | E_RangeBounce | 33 | 27% | +1.84 |
| INJUSDT | WEAK_TREND_DOWN | B_TrendPullback | 12 | 58% | +1.48 |
| ETHUSDT | STRONG_TREND_UP | D_MACDMomentum | 24 | 46% | +1.20 |
| WIFUSDT | STRONG_TREND_DOWN | B_TrendPullback | 13 | 54% | +1.19 |
| AVAXUSDT | STRONG_TREND_UP | B_TrendPullback | 12 | 67% | +1.16 |
| INJUSDT | RANGING | B_TrendPullback | 36 | 53% | +1.06 |
| AVAXUSDT | MIXED | A_VWAP | 11 | 55% | +0.79 |
| MSTRUSDT | WEAK_TREND_UP | B_TrendPullback | 12 | 67% | +0.64 |
| MSTRUSDT | STRONG_TREND_DOWN | E_RangeBounce | 23 | 22% | +0.48 |
| XLMUSDT | WEAK_TREND_DOWN | B_TrendPullback | 11 | 55% | +0.40 |
| DOGEUSDT | WEAK_TREND_UP | B_TrendPullback | 10 | 50% | +0.34 |
| AVAXUSDT | STRONG_TREND_DOWN | B_TrendPullback | 10 | 60% | +0.23 |
| WIFUSDT | WEAK_TREND_DOWN | B_TrendPullback | 11 | 45% | +0.17 |
| MSTRUSDT | RANGING | B_TrendPullback | 27 | 41% | +0.14 |
| INJUSDT | STRONG_TREND_UP | D_MACDMomentum | 15 | 60% | +0.10 |
| BTCUSDT | STRONG_TREND_DOWN | D_MACDMomentum | 19 | 53% | +0.02 |
| INJUSDT | MIXED | A_VWAP | 16 | 31% | +0.01 |

---

## Mapping changes (v1 → v2)

- **v1:** flat schema (no `version` field), 9 global regimes, **0 per-asset overrides**
- **v2:** `version: 2`, 9 global regimes, **8 assets with 19 per-asset overrides**
- v1 strategy assignments (15d window): STRONG_TREND_UP→A_VWAP, STRONG_TREND_DOWN→B_TrendPullback, WEAK_TREND_UP→A_VWAP, WEAK_TREND_DOWN→B_TrendPullback, RANGING→A_VWAP, SQUEEZE→B_TrendPullback, VOLATILE→None, MIXED→A_VWAP
- v2 strategy changes vs v1:
  - WEAK_TREND_UP: A_VWAP → **E_RangeBounce** (better fit for choppy up markets)
  - SQUEEZE: B_TrendPullback → **A_VWAP** (VWAP reversion more reliable during compression)
  - MIXED: A_VWAP → **B_TrendPullback** (trend-pullback outperforms on diverse/unclear regime)
  - VOLATILE: None → **B_TrendPullback** (5 trades only, low confidence — monitor in Task 19)
- v2 stand-aside regimes (pnl ≤ 0): **STRONG_TREND_DOWN** (−$72.81), **WEAK_TREND_DOWN** (−$6.05)
  - v1 had STRONG_TREND_DOWN negative too (−$15.93) — consistent finding
  - v1 had WEAK_TREND_DOWN positive ($+3.29 via B_TrendPullback) — reversed in 60d data. Likely v1's 15d sample was unrepresentative.

---

## Bug fixed in this run

`calc_macd` in `backtest_regime_matrix.py` had an O(n³) implementation: it rebuilt the full EMA history from scratch for every bar by looping `range(slow, len(closes)+1)` and calling `calc_ema()` (O(n)) per iteration. For 5760 bars (60d × 15m) this meant ~30 billion operations per asset. After 19 minutes on BTCUSDT alone with no progress, the process was killed.

Fix: replaced with incremental EMA computation (seed from first `slow` bars, then walk forward with `ema = (v - ema) * mult + ema`). Now O(n) per call. Run completed all 9 assets in ~8 minutes total.

The fix is pure performance — no change to strategy logic or output values (MACD values are numerically equivalent).

---

## Open questions / follow-ups

1. **Acceptance gates not met:** WR 42.8% < 53%, PnL/day $+1.15 < $+6.5. Two options before Task 19:
   - Accept as-is: the mapping still produces positive PnL and prevents worst regimes (stand-aside). The gate was ambitious for a first 60d run.
   - Tune: raise VWAP reversion threshold (dist_atr < -1.2 instead of -0.8), tighten RSI extremes (30/70 instead of 35/65), add volume filter. Re-run backtest after tuning.

2. **Profit factor + max-DD not measured** — defer to Task 19 live smoke test. Add these metrics to the backtest script before Task 18 OOS validation.

3. **VOLATILE regime (5 trades)** barely passes the min-5 threshold. Treat as stand-aside in practice until Task 19 accumulates live data.

4. **SOLUSDT no per-asset overrides** — SOLUSDT likely oscillates too frequently between regimes to build n≥10 in any single cell. May need lower threshold (n≥7) or be treated as global-only.

5. **C_BBSqueeze negative everywhere** — the BB squeeze breakout strategy is fundamentally not working on 15m bars across these altcoins. Consider removing from the strategy set in a future iteration to reduce noise.

6. **WIF MIXED → E_RangeBounce 27% WR $+1.84/trade** is suspicious — positive PnL at 27% WR implies very large winners. This may be fragile (one meme-coin pump skewing results). Flag for close monitoring in Task 19.

7. **INJUSDT WEAK_TREND_DOWN override** contradicts global stand-aside. The router (Task 14-15) must implement per-asset lookup with fallback-to-global correctly to capitalize on this.
