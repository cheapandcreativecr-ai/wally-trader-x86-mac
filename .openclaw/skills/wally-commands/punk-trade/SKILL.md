---
name: punk-trade
description: Estrategia A backtested ganadora — VWAP Reversion + MTF Trend Filter
  (WR 57%, PF 3.31, ~34min duration) [solo bitunix]
version: 1.0.0
metadata:
  openclaw:
    tags:
    - wally-trader
    - command
    - slash
    category: trading-command
    requires_toolsets:
    - terminal
    - subagents
---
<!-- generated from system/commands/punk-trade.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /punk-trade -->


Estrategia hourly **backtested ganadora** entre 3 candidatas (VWAP Reversion / BB Squeeze / ADX Pullback). Solo VWAP Reversion + MTF Trend Filter mostró rentabilidad consistente:

```
Backtest 15 días, 9 assets:
- WR 57.1% | Profit Factor 3.31 ⭐
- Avg PnL +$1.73/trade | Avg duration 34 min
- Avg WIN +$4.34 vs Avg LOSS -$1.75 (ratio 2.5:1)
- 7 trades en 15 días = SELECTIVA pero rentable
```

**Filosofía:** SELECTIVIDAD > frecuencia. NO fuerza 1 trade/hora — espera oportunidades A-grade. Esperá ~4-5 setups válidos por día en universo 9 assets.

## Lógica de la estrategia

1. **MTF macro filter (1h):** EMA(50) sobre 1h closes determina trend macro
   - Precio > EMA50 1h → solo buscar **LONGS contra-trend** (mean reversion al alza)
   - Precio < EMA50 1h → solo buscar **SHORTS contra-trend**

2. **Setup trigger (15m):**
   - Precio se aleja **>0.8×ATR del VWAP** en dirección CONTRA-trend macro
   - **RSI(14) en extremo:** >65 (SHORT) o <35 (LONG)

3. **Targets:**
   - **SL:** entry ± 0.5×ATR más allá del extremo (apretado)
   - **TP1:** vuelta al VWAP (50% close, típico 0.3-0.8% mov)
   - **TP2:** VWAP ± 0.5×ATR (50% close para continuación)

4. **R:R gate:** TP1/SL ≥ 1.0 obligatorio. Si menor → REJECT.

## Pasos que ejecuta Claude

1. **Profile guard (bitunix-only):**
   ```bash
   PROFILE=$(python3 .claude/scripts/profile.py get | awk '{print $1}')
   [ "$PROFILE" = "bitunix" ] || { echo "❌ Solo bitunix"; exit 1; }
   ```

2. **Scan watchlist** ejecutando el helper:
   ```bash
   python3 .claude/scripts/strategy_vwap_mtf.py --json
   ```

3. **Si hay setup válido:** despacha al agente `punk-trade-analyst` para:
   - Validación cruzada con macro_gate (eventos high-impact ±30 min)
   - Smart Money L/S check (Binance top traders Confirmation)
   - Output del setup completo + auto-log a signals_received.md

4. **Si NO hay setup:** mensaje "ESPERAR — próxima oportunidad típica en 1-3h"

5. **Argumento opcional `$ARGUMENTS`:**
   - `--asset SYMBOL` → scan único asset (ej. `/punk-trade --asset BTCUSDT`)
   - `--show-all` → muestra también los rejected con razón
   - texto libre → contexto extra al agente

## Output esperado

**Caso A — Hay setup válido:**
```
🎯 PUNK-TRADE — Setup VWAP-MTF detectado

🟢 LONG SOLUSDT
Entry: $145.20 | RSI: 32.1 | distance VWAP: -1.05σ
Macro trend (1h EMA50): UP (contra-trend reversal setup)

SL:  $144.50 (0.48%)
TP1: $146.10 (0.62%) — R:R 1.29
TP2: $146.80 (1.10%) — R:R 2.29

Sizing: $50 margin × 10x = $500 notional, 3.44 SOL
Risk: $2.40 si SL hit (1.20% capital)
Expected duration: 30-45 min (median backtest 34 min)

Macro gate: ✅ clear próximas 4h
Smart Money L/S: 0.95 (a favor del SHORT) ← bonus confirmación

📤 Auto-loggeado a signals_received.md
👉 Ejecutar manual en Bitunix:
   - SOLUSDT.P LONG @ market o limit 145.20
   - SL: 144.50 | TPs escalonados arriba
   - Cierre: /log-outcome SOLUSDT.P TP1|TP2|SL EXIT --pnl USD
```

**Caso B — No hay setup:**
```
⏳ PUNK-TRADE — Sin setup VWAP-MTF ahora

9 assets evaluados, ninguno cumplió:
- distance VWAP > 0.8σ contra-trend
- RSI extremo (>65 SHORT o <35 LONG)
- R:R TP1 ≥ 1.0

Top razones de rechazo:
- ETHUSDT: distance VWAP solo 0.3σ (no extremo)
- BTCUSDT: RSI 52 (neutral)
- DOGEUSDT: macro trend ambiguo

Próxima invocación recomendada: ~1h o cuando aparezca volatilidad en London/NY.
```

## Cadencia recomendada

Manual cada 30-60 min (más selectivo que /punk-hunt). O auto-loop:
```
/loop 60m /punk-trade
```

**Importante:** la estrategia es SELECTIVA por diseño. No esperés 1 setup cada hora. Esperás 4-5 setups VÁLIDOS por día en universo. Mejor menos trades A-grade que muchos B-grade.

## Comparativa con otros comandos bitunix

| Comando | Lógica | Frecuencia | WR backtest |
|---|---|---|---|
| `/signal` | Validación señal Discord externa | On-demand cuando llega | depende calidad señal |
| `/punk-hunt` | 4 confluencias Elite Crypto + Hyper Wave (necesita Neptune) | Cada ~1h forzada | 19.8% (proxies sin Neptune real) |
| **`/punk-trade`** ⭐ | **VWAP Reversion + MTF (NO necesita Neptune)** | **Selectiva 4-5/día** | **57.1% backtested** |

`/punk-trade` es la **opción más confiable** ahora porque:
- ✅ Backtested rentable con data real
- ✅ NO depende de Neptune privado
- ✅ Lógica simple y replicable
- ✅ Selectivo (solo A-grade setups)

## Reglas de seguridad

- **NUNCA** ejecuta el trade en Bitunix — solo loggea la recomendación
- **NUNCA** propone leverage > 10x
- **NUNCA** propone SL > 1% del entry
- Mismo gate macro/concurrente/daily-cap que `/signal`
- R:R mínimo TP1 ≥ 1.0 (sin esto, REJECT)

Si hay argumentos:

$ARGUMENTS
