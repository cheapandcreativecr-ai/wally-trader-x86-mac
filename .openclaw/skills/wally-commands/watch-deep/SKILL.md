---
name: watch-deep
description: 'Wally Trader command: /watch-deep'
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
<!-- generated from system/commands/watch-deep.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /watch-deep -->

Validación profunda de una pending order usando MCP TradingView — invocada
por `watcher_escalate.sh` headless cuando precio <0.3% del entry, o por usuario manual.

Uso: `/watch-deep <order_id>`

Pasos:

1. **Resuelve order:**
   ```bash
   python3 -c "
   from pending_lib import find_by_id
   import json
   r = find_by_id('$ID')
   print(json.dumps(r[1]) if r else '')
   "
   ```
   Si vacío → error "Order not found".

2. **Switch chart TV al asset correcto:**
   - `retail`, `retail-bingx`, `ftmo` BTCUSD/ETHUSD → `BINANCE:BTCUSDT.P` o ETH.
   - `fotmarkets` EURUSD/GBPUSD/etc → `OANDA:EURUSD` etc.
   - TF: retail/retail-bingx → 15m, fotmarkets → 5m.

3. **Lee indicadores con MCP:**
   - `mcp__tradingview__data_get_study_values` (busca RSI, BB, Donchian/Price Channel, ATR)
   - `mcp__tradingview__data_get_ohlcv` últimas 2 velas (para cierre verde/rojo)
   - Neptune si visible (opcional, solo informativo)

4. **Evalúa cada filter en `required_filters_at_trigger`:**
   - Construye tabla: `[filter_name] → PASS/FAIL con valor actual`
   - Ejemplo para retail LONG: RSI<35, precio toca DC Low(15) ±0.1%, BB lower touch, close verde.

5. **Decide:**
   - Si **todos PASS**:
     ```bash
     python3 -c "
     from pending_lib import find_by_id, update_status
     from notify_hub import notify, Urgency
     r = find_by_id('$ID'); profile, o = r
     update_status(profile, '$ID', 'triggered_go', note='all filters PASS')
     notify(Urgency.CRITICAL, 'triggered_go', {
         'order_id': '$ID', 'profile': profile, 'asset': o['asset'],
         'side': o['side'], 'entry': o['entry'], 'sl': o['sl'], 'tp1': o['tp1'],
         'filters_passed': 4, 'filters_total': 4,
     })
     "
     ```
     Luego dibuja en TV (entry/SL/TPs) usando `mcp__tradingview__draw_shape`.

   - Si **parcial (<4)**:
     ```bash
     python3 -c "
     from pending_lib import find_by_id, update_status
     r = find_by_id('$ID'); profile, o = r
     update_status(profile, '$ID', 'pending', note='filters X/4 — waiting')
     "
     ```
     No notify (heartbeat silent).

   - Si **error en MCP**:
     ```bash
     python3 -c "
     from pending_lib import find_by_id, update_status
     from notify_hub import notify, Urgency
     r = find_by_id('$ID'); profile, o = r
     update_status(profile, '$ID', 'check_error', note='MCP failure')
     notify(Urgency.WARN, 'degraded_watcher', {'order_id': '$ID', 'profile': profile, 'asset': o.get('asset')})
     "
     ```

6. **Output compacto** (headless context — mensaje corto):
   - `VERDICT: <triggered_go|pending|check_error>`
   - `Filters: 4/4 | 3/4 | ...`
   - `Notify: <channel list>`

NO preguntas al usuario. Headless-safe.
