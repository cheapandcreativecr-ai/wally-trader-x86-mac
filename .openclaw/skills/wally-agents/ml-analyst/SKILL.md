---
name: ml-analyst
description: Use cuando el usuario pida "ML score", "ml predict", "qué dice el modelo",
  "probabilidad de TP", o quiera el score supervisado del setup actual. Ejecuta el
  predictor XGBoost entrenado sobre 1yr+ de BTC 15m y reporta probabilidad TP-first
  para LONG y SHORT.
version: 1.0.0
metadata:
  openclaw:
    tags:
    - wally-trader
    - agent
    - trading
    category: trading-agent
    requires_toolsets:
    - terminal
---
<!-- generated from system/agents/ml-analyst.md by adapters/openclaw/transform.py -->
<!-- Original CC tools: Bash, Read -->


# ML Analyst

Usa el modelo supervisado XGBoost (`scripts/ml_system/supervised/`) para predecir la probabilidad de que un setup termine en TP antes que SL, basado en condiciones actuales de mercado.

## Qué hace el modelo

- Entrenado sobre histórico 1 año BTCUSDT 15m
- 2 clasificadores binarios calibrados: LONG y SHORT
- 12 features: RSI, BB pos, Donchian dist, vol z-score, ATR%, vela actual, hora/día, momentum
- Target: TP(2.5×SL) hit antes que SL(1.5×ATR) en próximas 16 velas (4h)

## Ejecución

```bash
# Modo auto — descarga data reciente y predice sobre último cierre
python3 scripts/ml_system/supervised/predict.py --auto

# Modo JSON
python3 scripts/ml_system/supervised/predict.py --auto --json

# Modo explícito — features a mano
python3 scripts/ml_system/supervised/predict.py \
    --rsi 32 --bb-pos -0.9 \
    --donchian-dist-low 0.0008 --donchian-dist-high 0.011 \
    --vol-z 1.2 --atr-pct 0.0048 \
    --close-to-open 0.0003 --body-vs-range 0.7 \
    --hour-mx 9 --day 1 \
    --mom3 0.4 --mom12 1.1
```

Si el modelo no existe aún:
```bash
python3 scripts/ml_system/supervised/train.py --days 365
```
(Descarga ~100MB de Binance, entrena en ~2 min, guarda en `supervised/model/`.)

## Output

```
LONG  → 58/100 (🟡 NEUTRAL)
SHORT → 34/100 (🔴 BAJO)
📍 BIAS LONG si setup técnico 4/4 LONG aparece, tiene edge.
```

## Interpretación — NUNCA como único filtro

| Probabilidad | Acción |
|---|---|
| <35% | Bajo — probable no-TP. Si el setup técnico 4/4 igual aparece → pasar o size 50% |
| 35-55% | Neutral — decisión por técnico puro |
| 55-70% | Favorable — el modelo confirma el setup técnico |
| >70% | Fuerte — edge histórico alto |

**Reality check:**
- AUC típico en crypto 15m: 0.55-0.62. Más es sospechoso de overfitting.
- El modelo sube probabilidad cuando TU setup técnico ya es válido — NO lo uses para encontrar setups nuevos.
- Recalibrar cada 2-4 semanas con `/ml-train` para adaptarse al régimen actual.

## Integración

- **trade-validator** puede consultarlo como 5° filtro cuando los 4 técnicos estén alineados
- **morning-analyst** puede reportar el score al inicio del día junto con sentiment
- Si ML score <40 y setup técnico es GO → reportar como GO con warning y size reducida
