---
name: ml
description: Score ML supervisado del setup actual (XGBoost, probabilidad TP-first)
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
<!-- generated from system/commands/ml.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /ml -->


Invoca el agente `ml-analyst` para predecir la probabilidad de TP-first sobre las condiciones actuales de BTC 15m.

Ejecuta `python3 scripts/ml_system/supervised/predict.py --auto` por debajo, que:
1. Descarga últimas 200 velas 15m de Binance
2. Calcula 12 features (RSI, BB, Donchian, volumen, ATR, vela, hora, momentum)
3. Predice con modelo XGBoost calibrado
4. Reporta score LONG y SHORT (0-100) + recomendación

Útil como **5° filtro** cuando los 4 filtros técnicos están alineados — confirma o cuestiona el setup.

Si el modelo no existe aún, ejecuta `/ml-train` primero.

$ARGUMENTS
