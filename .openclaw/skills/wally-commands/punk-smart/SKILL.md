---
name: punk-smart
description: Regime-aware smart router — detecta contexto del mercado por asset y
  ejecuta la estrategia ganadora del backtest matrix [solo bitunix]
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
<!-- generated from system/commands/punk-smart.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /punk-smart -->


**Regime-aware smart trader** — el primer comando del sistema que CONOCE qué estrategia funciona en qué contexto, basado en backtest matrix de 5 estrategias × 7 contextos.

```
Backtest 15 días, 9 assets, 77 trades siguiendo mapping ganador:
- WR 49.4% | PnL +$84.61 (+42% capital en 15d)
- Avg +$1.10/trade | 5.1 trades/día ✅ alineado filosofía
- Proyección mensual: +$124 (62% capital/mes)
```

## Mapping ganador (auto-loaded de regime_mapping.json)

| Regime detectado | Strategy aplicada | Backtest WR | Avg PnL/trade |
|---|---|---|---|
| **STRONG_TREND_UP** | A_VWAP Reversion + MTF | 54% | +$2.54 |
| **RANGING** | A_VWAP Reversion + MTF | 56% | +$2.68 ⭐ |
| **MIXED** | A_VWAP Reversion + MTF | 45% | +$0.63 |
| **WEAK_TREND_DOWN** | B_Trending Pullback | 53% | +$0.22 |
| **SQUEEZE** | B_Trending Pullback | 45% | +$0.54 |
| **STRONG_TREND_DOWN** | ❌ STAND ASIDE | — | NEGATIVE |
| **WEAK_TREND_UP** | ❌ STAND ASIDE | — | NEGATIVE |
| **VOLATILE** | ❌ STAND ASIDE | — | INSUFFICIENT DATA |

## Diferencia con `/punk-trade` y `/punk-hunt`

| Comando | Lógica |
|---|---|
| `/signal` | Valida señal Discord externa |
| `/punk-hunt` | 4 confluencias Elite Crypto (necesita Neptune) — **WR 19.8% backtest** ⚠️ |
| `/punk-trade` | VWAP fija (sin regime detection) — **WR 57% backtest** |
| **`/punk-smart`** ⭐ | **Regime detection + best strategy per context** — **WR 49% pero rentable consistente** |

`/punk-smart` es la **opción más inteligente** porque:
- ✅ Sabe cuándo NO operar (3 regimes "STAND ASIDE")
- ✅ Aplica la estrategia óptima validada para el regime actual
- ✅ Se adapta automáticamente al cambio de mercado
- ✅ Mapping basado en backtest real, no intuición

## Pasos que ejecuta Claude

1. **Profile guard (bitunix-only):**
   ```bash
   PROFILE=$(python3 .claude/scripts/profile.py get | awk '{print $1}')
   [ "$PROFILE" = "bitunix" ] || { echo "❌ Solo bitunix"; exit 1; }
   ```

2. **Run smart router:**
   ```bash
   python3 .claude/scripts/punk_smart_router.py --json
   ```

3. **Si hay setups:** despacha al agente `punk-smart-analyst` para validación cruzada (macro_gate, smart money L/S, sizing) + auto-log signals_received.md

4. **Si NO hay setups (NO_SETUP en todos):** mensaje "regime tradeable detectado pero sin trigger actual — esperar 30-60 min y re-run"

5. **Si todos STAND_ASIDE:** mensaje "todos los regimes son STAND_ASIDE en backtest — mercado actual no operable, esperar cambio de regime"

6. **Argumento opcional `$ARGUMENTS`:**
   - `--asset SYMBOL` → scan único asset
   - `--show-all` → muestra también STAND_ASIDE / NO_SETUP con razón
   - texto libre → contexto extra al agente

## Output esperado

**Caso A — Hay setups:**
```markdown
🧠 PUNK-SMART — Regime-aware setup detection

✅ 2 SETUP(S) ENCONTRADO(S):

#1 🟢 LONG ETHUSDT (regime: RANGING, strategy: A_VWAP)
   Entry: 2375.40 | Backtest: 56% WR / +$2.68 per trade
   SL:  2370.20 (0.22%)
   TP1: 2382.10 (0.28%) — R:R 1.30
   TP2: 2389.50 (0.59%) — R:R 2.71

#2 🔴 SHORT INJUSDT (regime: RANGING, strategy: A_VWAP)
   Entry: 3.681 | Backtest: 56% WR / +$2.68 per trade
   SL:  3.700 (0.52%)
   TP1: 3.665 (0.43%) — R:R 0.84
   TP2: 3.650 (0.84%) — R:R 1.65

📊 Sizing recomendado: $100 margin × 10x = $1,000 notional
   Risk per trade: ~$1.20-2.50 (0.6-1.3% capital)
   Expected PnL per trade: +$1.10 (basado en backtest WR 49%)

📤 Auto-loggeado a signals_received.md (top setup)
👉 Ejecutar manual #1 en Bitunix:
   - ETHUSDT.P LONG @ 2375.40, leverage 10x
   - SL: 2370.20 | TPs escalonados arriba
   - Cierre: /log-outcome ETHUSDT.P TP1|TP2|SL EXIT --pnl USD
```

**Caso B — Regime tradeable pero sin setup actual:**
```markdown
⏳ PUNK-SMART — Regime tradeable pero sin trigger AHORA

7 assets con regime favorable (RANGING/STRONG_TREND_UP/SQUEEZE/MIXED) pero sus
estrategias específicas no triggean en este momento.

Razones típicas:
- VWAP Reversion necesita: precio >0.8σ del VWAP + RSI extremo (no presente)
- Trending Pullback necesita: pullback EMA21 + RSI cross 40/60 (no presente)

Próxima invocación: 30-60 min cuando aparezca extremo o pullback.

Assets STAND_ASIDE (regime malo): SOLUSDT, WIFUSDT (WEAK_TREND_UP)
```

**Caso C — Todo STAND_ASIDE:**
```markdown
🚫 PUNK-SMART — Mercado NO operable AHORA

Todos los assets evaluados están en regime con backtest negativo:
- 5 assets en STRONG_TREND_DOWN (estrategias pierden en este regime)
- 4 assets en VOLATILE (insuficiente data backtest)

Recomendación: ESPERAR cambio de regime (típicamente 2-4h).
Re-evaluar con `/punk-smart` después de London open o NY open.
```

## Cadencia recomendada

Manual cada 30-60 min, o auto-loop:
```
/loop 60m /punk-smart
```

Más selectivo que `/punk-hunt`, MÁS confiable porque cada decisión está respaldada por backtest.

## Reglas de seguridad

- **NUNCA** ejecuta el trade — solo loggea recomendación
- **NUNCA** propone leverage > 10x ni SL > 1.5% del entry
- Si regime es STAND_ASIDE → NO recomienda ese asset (regla anti-loss)
- R:R mínimo TP1 ≥ 1.0 (sin esto, REJECT)
- Auto-respeta concurrent slots (max 2) y daily cap (max 10)

## Re-calibrar mapping (cuando hayas acumulado más data real)

```bash
# Re-correr backtest matrix para actualizar el mapping
python3 .claude/scripts/backtest_regime_matrix.py
# Esto actualiza .claude/scripts/regime_mapping.json
# La próxima invocación de /punk-smart usará el nuevo mapping
```

Idealmente re-correr cada semana o después de evento macro relevante (FOMC, CPI).

Si argumentos:

$ARGUMENTS
