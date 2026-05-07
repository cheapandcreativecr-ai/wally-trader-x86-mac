---
name: ml-train
description: Re-entrena el modelo ML supervisado (descarga data Binance + XGBoost
  fit)
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
<!-- generated from system/commands/ml-train.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /ml-train -->


Re-entrena los 2 clasificadores XGBoost (LONG y SHORT) del sistema supervisado.

```bash
python3 scripts/ml_system/supervised/train.py --days 365 $ARGUMENTS
```

Flags opcionales:
- `--days 730` → 2 años de historia
- `--interval 1h` → otro timeframe
- `--refresh` → ignora cache y redescarga
- `--lookahead 24` → ventana hacia adelante (default 16 velas = 4h)

Duración típica: 2-4 minutos (mayoría en descarga + feature engineering).

Ejecutar cada 2-4 semanas o cuando cambie el régimen significativamente.

Output:
- Modelos guardados en `scripts/ml_system/supervised/model/`
- Métricas (AUC, LogLoss, Brier) en `metrics.json`
- Reality check automático que warna si AUC es sospechosamente alto (posible overfitting)
