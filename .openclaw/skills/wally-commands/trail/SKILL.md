---
name: trail
description: Calcula nivel de Trailing Stop con EMA(20) para un runner abierto (TP3)
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
<!-- generated from system/commands/trail.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /trail -->


Modo de salida #4 según el PDF "Manual del Buen Trader Algorítmico" (PIEZA 03):
trail dinámico con EMA(20) que captura más rally en trades trending.

## Cuándo usarlo

- Tras cerrar TP1 + TP2, dejaste 20% como runner
- Régimen actual es TREND (ADX>25) → trailing aprovecha el momentum
- Quieres salir cuando el momentum se rompa, no en target fijo

## Argumentos esperados

`/trail <side> <entry> [ema_length]`

- `side`: `long` o `short`
- `entry`: precio de entrada del trade
- `ema_length`: opcional, default 20

Ejemplos:
- `/trail long 96450`
- `/trail short 78200 21`

## Protocolo

1. Lee `.claude/active_profile` para conocer profile y símbolo
2. Profile retail/ftmo → bars 15m. Profile fotmarkets → bars 15m (trend TF, no 5m de entry)
3. Pull OHLCV via MCP TradingView:
   - `chart_set_timeframe 15`
   - `data_get_ohlcv summary=false count=80`
4. Guarda en `/tmp/bars15m.json` (formato compact `[{h,l,c}, ...]`)
5. `quote_get` → precio actual
6. Ejecuta:
   ```bash
   python3 .claude/scripts/trailing_stop.py \
     --file /tmp/bars15m.json \
     --side <side> \
     --entry <entry> \
     --current <current_price> \
     --ema <ema_length>
   ```
7. Reporta:
   - `EMA(N)` actual
   - `Trail level` = mismo valor (donde saldrías si toca)
   - `Distance %` del precio actual al trail
   - `Slope` (up/down/flat) — si va contra ti, alerta
   - `ACTION`:
     - `HOLD` → mantén el runner, todo OK
     - `HOLD_WARN` → EMA acercándose contra ti, vigilar próximas velas
     - `EXIT_TRAIL` → salir AHORA, el precio tocó EMA
     - `INVALID` → el trade no está en profit, NO usar trailing aún

## Output

```
🎯 TRAILING STOP — EMA(20) 15m

Side: LONG | Entry: 96,450 | Current: 98,120
Profit flotante: +1.73%

EMA(20) 15m: 97,820
Trail level: 97,820 (donde saldrías)
Distance: +0.31% (precio sobre EMA)
EMA slope: up ✅

ACTION: HOLD — momentum intacto, mantén runner

Vigilancia: si EMA empieza a bajar o slope cambia a flat → preparar exit manual
```
