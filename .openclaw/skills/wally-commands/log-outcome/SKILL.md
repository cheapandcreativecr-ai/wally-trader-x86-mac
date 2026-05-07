---
name: log-outcome
description: Cierra el outcome de una señal Bitunix abierta en signals_received.md
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
<!-- generated from system/commands/log-outcome.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /log-outcome -->


Cierra el outcome de una señal Bitunix previamente registrada con `/signal` (auto-log).

## Argumentos esperados

- `SYMBOL` — el símbolo (ej. BTCUSDT). Obligatorio.
- `OUTCOME` — uno de `TP1`, `TP2`, `TP3`, `SL`, `manual`. Obligatorio.
- `EXIT_PRICE` — precio de salida real (numérico). Obligatorio.
- `--id N` — opcional. Si hay múltiples señales abiertas del mismo símbolo, elegir cuál.
- `--pnl USD` — opcional. PnL en dólares. Si no se pasa, queda como `_calc_pendiente_` y el usuario lo edita manualmente.

## Comportamiento

- Solo aplica a `WALLY_PROFILE=bitunix`. En otro profile, mensaje informativo.
- Encuentra la entrada más reciente abierta de SYMBOL (con outcome `_pendiente_`).
- Si hay 2+ abiertas, lista los `--id` y pide al usuario que re-ejecute con `--id N`.
- Update `signals_received.md` y `signals_received.csv` con el outcome.

## Ejemplos

```bash
/log-outcome BTCUSDT TP1 75050.00
/log-outcome ETHUSDT SL 2800.50 --pnl -15.20
/log-outcome BTCUSDT TP2 76000 --id 2 --pnl 45.87
```

## Ejecución

```bash
WALLY_PROFILE=bitunix .claude/scripts/.venv/bin/python .claude/scripts/bitunix_log.py append-outcome $ARGUMENTS
```

Argumentos del usuario:

$ARGUMENTS
