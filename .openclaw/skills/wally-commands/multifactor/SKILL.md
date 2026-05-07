---
name: multifactor
description: Multi-Factor score 0-100 (Momentum + Volatility + Trend Quality + Volume).
  Meta-score complementario al ML XGBoost.
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
<!-- generated from system/commands/multifactor.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /multifactor -->


Pasos que ejecuta Claude:

1. **Pull bars del TF base de la estrategia activa:**
   - Profile retail/retail-bingx/ftmo → 15m (Mean Reversion / Donchian)
   - Profile fotmarkets → 5m (Fotmarkets-Micro)
   ```
   mcp__tradingview__chart_set_timeframe <TF>
   mcp__tradingview__data_get_ohlcv summary=false limit=250
   ```
   Guardar a `/tmp/bars.json`.

2. **Calcular score:**
   ```bash
   python3 .claude/scripts/multifactor_score.py --bars-file /tmp/bars.json
   ```

   Si quieres filtrar por side específico:
   ```bash
   python3 .claude/scripts/multifactor_score.py --bars-file /tmp/bars.json --side long
   ```

3. **Interpretar output:**
   - **TOTAL > +70** → LONG conviction ALTA
   - **TOTAL > +50 < +70** → LONG conviction MEDIA
   - **TOTAL entre -30 y +30** → FLAT, no operar
   - **TOTAL < -50** → SHORT conviction MEDIA
   - **TOTAL < -70** → SHORT conviction ALTA

4. **Cross-check con ML score (`/ml`):**
   ```bash
   python3 scripts/ml_system/supervised/predict.py --side long
   ```

   Matriz de decisión:
   | MultiFactor | ML | Acción |
   |---|---|---|
   | >70 | >60 | **MAX conviction**: full size |
   | 50-70 | >60 | Conviction MEDIA: size 75% |
   | >70 | <40 | **DIVERGEN**: flag — reducir size 50% o skip |
   | <30 | cualquiera | Setup débil — esperar |
   | 50-70 | 40-60 | Borderline — necesita 4/4 filtros perfectos |

5. **Output al usuario:**
   - Tabla con breakdown por factor (momentum, vol, trend, volume)
   - Direction (LONG/SHORT/NEUTRAL) + conviction (ALTA/MEDIA/BAJA/FLAT)
   - Recomendación cruzando con ML score si está disponible

## Casos de uso

- **Pre-entry validation:** después de los 4 filtros técnicos, este score da una segunda señal independiente.
- **Trade selection:** entre múltiples setups posibles, elegir el que tiene multi-factor más alto en su dirección.
- **Si ML predict no está disponible:** multi-factor puede sustituir como meta-score (hasta tener más data para reentrenar).

## Por qué este score, no solo el ML

El ML XGBoost predice probabilidad TP-first basado en features históricas. El multi-factor da una visión más interpretable y cruzable:
- ML puede sobre-fit a un régimen pasado.
- Multi-factor es regla mecánica → más estable bajo regime change.
- Cuando ambos coinciden → **diversificación de modelo** = mayor robustez.
- Cuando divergen → **flag importante** que la estrategia merece scrutinio extra.

## Limitaciones

- Requiere 50+ bars (idealmente 200+ para volatility percentile decente).
- Volume score solo funciona si el feed TV reporta volumen (forex en algunos brokers no).
- ADX calculado es simplificado vs ADX clásico (usa proxy `avg_move/atr`). Para precisión, usa `/regime` que tiene ADX completo.

$ARGUMENTS
