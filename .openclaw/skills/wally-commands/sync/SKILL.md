---
name: sync
description: 'Wally Trader command: /sync'
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
<!-- generated from system/commands/sync.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /sync -->

Sincroniza pending_orders.json con mt5_state.json. Marca fills y expirations.

Pasos:
1. Verifica profile==ftmo
2. Lee state y pending
3. match_pending_to_positions(pending, state.positions):
   - Por cada match → pending[i].status = "filled", agregar ticket MT5
4. Por cada pending con proposed_at + expiry_minutes < now:
   - status = "expired"
5. Save pending_orders.json
6. Output summary:
   - "X órdenes filled hoy (tickets: ...)"
   - "Y órdenes expired"
   - "Z órdenes still queued"
7. Si EA offline > 1h: Pide al usuario "Pega output de MT5 Terminal → Trade + History → lo parseo con regex y actualizo mt5_state.json manualmente con source=manual_paste"

8. **DUAL-WRITE A NOTION FTMO DB (si Notion MCP activo):**
   - Lee `.claude/.env` para `NOTION_FTMO_DB_ID`. Verifica acceso a tools `mcp__notion_*`
   - Para cada pending cuyo status cambió en este /sync (queued/sent_to_ea → filled, o expired):
     - Si pending tiene `notion_page_id` (lo guardó /order previo):
       - Usa `mcp__notion__update_page` con page_id=<notion_page_id>
       - Update columnas: Status=<new>, Ticket MT5=<ticket>, Entry actualizado si difiere, Result si ya cerró
     - Si no tiene notion_page_id (pending legacy pre-Notion): skip (queda como pending en memoria local solo)
   - Para trades nuevos cerrados hoy detectados en `closed_today` sin pending matching (trades manuales en MT5 no generados por /order):
     - Crear row nueva en Notion FTMO DB con Status=closed, Result calculado de close_reason
   - Si Notion write falla: warning + continúa sin bloquear
