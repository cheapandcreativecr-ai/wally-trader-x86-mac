---
name: trades
description: 'Wally Trader command: /trades'
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
<!-- generated from system/commands/trades.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /trades -->

Dashboard del estado MT5 del profile FTMO.

Pasos:
1. Verifica profile==ftmo
2. Lee state: `python3 scripts/mt5_bridge.py load-state --path .claude/profiles/ftmo/memory/mt5_state.json`
   (O directamente usando mt5_bridge imports desde un script inline)
3. Lee pending: `.claude/profiles/ftmo/memory/pending_orders.json`
4. Guardian status: `python3 scripts/guardian.py --profile ftmo --action status`
5. Verifica EA heartbeat con ea_is_alive()
6. Formatea dashboard:

```
═════════════════════════════════════════════
[FTMO $10k] — MT5 STATE @ <HH:MM:SS MX>
Account: Balance $<B> | Equity $<E> (<delta%>)
EA heartbeat: <Xs> ago <✓|⚠️|✗>

POSICIONES ABIERTAS (<N>)
  #<ticket> <sym> <TYPE> <vol> @ <open> → SL <sl> / TP <tp>
           PnL: <sign>$<profit> (<pct>%) • Current: <cur>

ÓRDENES PENDIENTES MT5 (<N>)
  ...

CLAUDE QUEUE (<N>)
  <id> [<status>] <symbol> <side>

CERRADAS HOY (<N>)
  #<ticket> <sym> <TYPE> <vol> → <close_reason> <sign>$<profit> (<open_time>→<close_time>)

DAILY PnL: <sign>$<d> (<pct>% / -3% limit)
TRAILING DD: $<dd> (<pct>% / 10% limit)
TRADES HOY: <cerradas> cerrado + <abiertas> abierto = <total>/2
═════════════════════════════════════════════
```

7. Si EA offline (>1h), muestra:
```
⚠️ EA OFFLINE — último state: <X>
Última orden propuesta: <id> [<status>]
Pega estado MT5 actual o corre /sync
```

8. **CROSS-REFERENCE CON NOTION FTMO DB (si Notion MCP activo):**
   - Lee `.claude/.env` para `NOTION_FTMO_DB_ID`. Verifica acceso a tools `mcp__notion_*`
   - Si disponible:
     - Query `mcp__notion__query_database` con filter `Date == today` (timezone CR)
     - Para cada row hoy: cross-reference con mt5_state + pending_orders
     - Detecta discrepancias:
       - Row Notion con Status=filled pero no aparece en state.positions ni closed_today → flag warning
       - Position en MT5 no presente en Notion (trade manual sin /order) → sugerir /sync para agregarla
     - Agrega sección al dashboard:
       ```
       NOTION MIRROR (hoy)
         Rows en Notion hoy: N
         Sincronización: ✓ OK / ⚠️ <N> discrepancias
       ```
   - Si query falla: warning silent + continúa sin sección Notion
