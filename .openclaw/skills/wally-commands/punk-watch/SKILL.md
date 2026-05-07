---
name: punk-watch
description: Vigila trade activo bitunix con análisis adaptativo de TPs/SL + forecast
  de volatilidad próximas horas [solo bitunix]
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
<!-- generated from system/commands/punk-watch.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /punk-watch -->


Vigilancia adaptativa del trade activo en profile `bitunix`. Recalcula TPs/SL contextuales y proyecta catalysts próximas 4-12h para sugerir si CERRAR ahora o AGUANTAR.

A diferencia de `/punk-hunt` (genera entries) y `/signal` (valida señales Discord), este comando **gestiona la salida** del trade ya abierto.

## Filosofía

> "Ganar lo que da el mercado, no lo que yo quiero."

- Si contexto fortaleció desde entry → **AMPLIAR TPs** (dejar correr más profit)
- Si contexto debilitó → **REDUCIR TPs** o **cerrar antes** (preservar lo ganado)
- Si próximas horas hay catalyst macro → **ajustar timing** (esperar London open o cerrar antes de NFP)
- Si Asia muerta sin catalysts → **cerrar parcial**, no dormir esperando

## Pasos que ejecuta Claude

1. **Profile guard:**
   ```bash
   PROFILE=$(python3 .claude/scripts/profile.py get | awk '{print $1}')
   [ "$PROFILE" = "bitunix" ] || { echo "❌ Solo bitunix"; exit 1; }
   ```

2. **Detectar trade activo:** lee `signals_received.csv` para `outcome = _pendiente_`. Si NO hay → mensaje "no hay trade activo, nada que vigilar". Si hay 2 → vigilar ambos.

3. **Despacha al agente `punk-watch-analyst`** con las fases documentadas.

4. **Argumento opcional `$ARGUMENTS`:**
   - `--symbol SYMBOL` → vigilar solo ese asset (si hay 2 abiertos)
   - `quick` → análisis rápido sin forecast
   - texto libre → contexto extra al agente

## Output esperado

```markdown
🔄 PUNK-WATCH — ETH SHORT (entry hace 1h 23min)

## Estado actual
- Posición: 0.420 ETH SHORT @ $2,380.26 (margin $100)
- Precio: $2,378.90 | PnL: +$0.57 (+0.28% capital)
- SL actual: $2,380.26 (BE post-DUREX) | TP1: $2,362 | TP2: $2,350 | TP3: $2,335
- Slot 1/2 | Time elapsed: 1h 23min

## Análisis contextual ahora vs entry

| Factor | At entry | AHORA | Δ |
|---|---|---|---|
| Hour factor (CR) | 0.6 (Asia early) | 0.5 (Asia muerta) | -0.1 ⚠️ |
| Regime | RANGING (23%) | TRENDING_UP (85%) | empeoró ⚠️ |
| Volatility (ATR%) | 0.42 | 0.38 | bajó (vol cayendo) |
| Smart Money L/S | 1.05 | 0.95 | mejoró ✅ (smart money rotando short) |
| **Context multiplier** | **0.30** | **0.35** | **+17% ✅** |

## TPs adaptativos recalculados

| Nivel | Original (R/R fijo) | Adaptativo AHORA | Δ |
|---|---|---|---|
| TP1 | $2,362.00 (-0.77%) | **$2,374.40 (-0.25%)** | EXTEND ⚠️ +60% más cerca |
| TP2 | $2,350.00 (-1.27%) | $2,371.00 (-0.39%) | EXTEND |
| TP3 | $2,335.00 (-1.90%) | $2,365.50 (-0.62%) | EXTEND |

Cambio significativo (>15% threshold): ✅ **3 TPs cambiaron** — sugerencia ABAJO.

## 📅 Forecast próximas 4-12h

| Hora CR | Evento | Volatilidad esperada | Implicación trade |
|---|---|---|---|
| 23:00-05:00 | Asia death zone | BAJA — lateralización probable | Lateral, no esperar TP grande |
| 02:00 | Funding payment ETH (cripto) | Pequeño spike típico | Posible mecha — DUREX ya cubre |
| 05:00-06:00 | London Open transition | MEDIA — empieza a despertar | Catalyst inicial |
| **06:00-09:00** | **London Open + NY pre-market** | **ALTA** | **CATALYST MAYOR** ⭐ |
| 09:00-12:00 | NY/London overlap | MUY ALTA (mejor liquidez del día) | Posible TP2/TP3 hit |

**Macro events próximas 12h:** ✅ Ninguno high-impact (verificado con `macro_gate.py`)

## 🎯 RECOMENDACIÓN

**Caso A — Si querés aguantar (esperás TP grande):** ✅ válido
- Catalyst MAYOR mañana CR 06:00-09:00 puede empujar a TP2/TP3 originales
- Risk: $0 (DUREX ya activado, SL en BE)
- Tiempo: 7-10h overnight

**Caso B — Si querés cerrar ahora (capturar lo seguro):** ✅ también válido
- TP1 adaptativo $2,374.40 está -$4.50 del precio actual — alta probabilidad próximas 1-2h
- Cerrar 40% en $2,374 = +$2.69 asegurado, runner 60% sigue corriendo
- Útil si querés dormir tranquilo sin pendiente

**Mi recomendación:** **Caso B** (cerrar 40% en TP1 adaptativo $2,374.40, mantener runner 60%)
- Justificación: contexto sigue débil (mult 0.35), vol cayendo
- TPs originales requieren London catalyst (no garantizado)
- DUREX ya cubre downside → upside del runner es free option
```

## Reglas

- **NUNCA modifica el trade en Bitunix automáticamente** — solo sugiere
- Si TP adaptativo < precio actual ya rebasado → marcar como "MIGHT HAVE BEEN"
- Si SL viejo ya tocado por wick → alertar inmediato
- Si contexto cambió >30% → recomendar acción inmediata (no esperar próximo /punk-watch)

## Cadencia recomendada

Manual cada 30-60 min mientras hay trade activo. O auto-loop:
```
/loop 30m /punk-watch
```

Si argumento opcional, contexto adicional:

$ARGUMENTS
