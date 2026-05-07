---
name: macross
description: Detecta señal MA Crossover (EMA 9/21) — 3ª estrategia para régimen TRENDING
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
<!-- generated from system/commands/macross.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /macross -->


3ª estrategia del Manual del Buen Trader Algorítmico (PIEZA 03 página 82): Cruce de Medias.

## Cuándo usarla

- `/regime` reporta TREND_LEVE o TREND_FUERTE (ADX > 25)
- Mean Reversion no aplica (no hay rango definido)
- Breakout ya disparó o no es claro el nivel

## Lógica

- **LONG**: EMA(9) cruza ARRIBA de EMA(21) en la última vela cerrada AND close > EMA(21)
- **SHORT**: EMA(9) cruza ABAJO de EMA(21) en la última vela cerrada AND close < EMA(21)
- **NEUTRAL**: EMAs sin cruce o sin alineación con precio

## Salida del trade (usar mismo modelo que Mean Reversion)

- SL: 1.5 × ATR(14)
- TP1: 1.5R (40%) → SL a BE
- TP2: 3R (40%)
- TP3 (20%): trailing EMA(21) — comando `/trail` con `--ema 21`

## Protocolo

1. Lee `.claude/active_profile`
2. TF según profile:
   - retail → 15m bars (300)
   - ftmo → 15m bars del asset
   - fotmarkets → 15m bars del asset
3. `data_get_ohlcv` count=80, save a `/tmp/bars_macross.json` formato `[{c}, ...]`
4. Ejecuta:
   ```bash
   python3 .claude/scripts/macross.py --file /tmp/bars_macross.json --quick
   ```
5. Reporta SIGNAL: LONG / SHORT / BULL_TREND_NO_CROSS / BEAR_TREND_NO_CROSS / NEUTRAL
6. Si LONG/SHORT → mostrar entry, SL ATR-based, TPs, recomendar `/risk` para sizing

## Output esperado

```
🔀 MA CROSSOVER — EMA(9/21)

Signal: LONG
EMA(9): 76,500 | EMA(21): 76,200 | Close: 76,650
Cross: EMA(9) cruzó arriba de EMA(21) esta vela
Trend filter: ✅ close > EMA(21)

Recomendación:
- Entry: 76,650 (close de vela cross)
- SL: 76,500 - 1.5×ATR (calcula con script)
- TP1: 1.5R (40%, SL→BE)
- TP2: 3R (40%)
- TP3: trail EMA(21) — usa /trail long 76650 21 cuando TP2 cierre

⚠️ Validar antes con /regime: ADX debe ser >25 y dirección consistente con el cross.
```
