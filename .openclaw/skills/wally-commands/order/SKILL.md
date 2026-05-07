---
name: order
description: 'Wally Trader command: /order'
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
<!-- generated from system/commands/order.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /order -->

Encola una orden limit virtual para el profile activo. El watcher la vigila
hourly hasta trigger/invalidación.

Uso:
- `/order` — infiere params del último análisis (si hay `/morning` reciente en la conversación).
- `/order BTCUSDT.P LONG 77521 sl=77101 tp=78571 ttl=6h`
- `/order BTCUSDT.P LONG 77521 sl=77101 tp=78571 invalid=76900 ttl=6h`
- `/order BTCUSDT.P LONG 77521 ... --real` (solo retail; en v1 imprime "stub")
- `/order BTCUSDT.P LONG 77521 ... --check-regime` (invalida si régimen cambia)

Pasos que ejecuta Claude:

1. **Lee profile activo:** `PROFILE=$(python3 .claude/scripts/profile.py get)`
2. **Parsea args:** Si vacíos, busca último setup en la conversación con bloque
   `ENTRY|SL|TP|INVALIDATION`. Si no encuentra → error "Dame params explícitos o corre /morning primero".
3. **Valida profile-specific:**
   - `ftmo` → **DELEGA** al flow existente (guardian.py + EA bridge). Si
     `PROFILE=ftmo`, imprime "Para FTMO usa el flow existente — ver mt5_bridge"
     y aborta.

     > **FTMO legacy flow (referencia):** Carga params → guardian.py check →
     > preview ASCII + confirmación YES → append pending_orders.json →
     > mt5_bridge.py ea-status → si EA vivo: append mt5_commands.json, espera
     > 10s, verifica processed+result.ok; si EA offline: status=manual_pending,
     > imprime box para copiar a MT5 manualmente → dual-write a Notion FTMO DB
     > (si NOTION_FTMO_DB_ID en .claude/.env + mcp__notion_* disponible).

   - `retail`:
     - Sanity: SL lado correcto, TP lado correcto, risk_pct ≤ 2.
     - `order_lib.sizing_for_profile('retail', entry, sl, 18.09)` → qty/risk.
     - Si `--real` → imprimir **"⚠️ --real no implementado en v1, orden virtual only"** y continuar.
   - `retail-bingx`:
     - Igual que retail pero capital=0.93 (lee de config.md).
     - `--real` no aplica (BingX sin API integrada). Siempre virtual.
   - `fotmarkets`:
     - `python3 .claude/scripts/fotmarkets_guard.py check` → si BLOCK, abortar con reason.
     - Verifica asset in `allowed_assets` de la phase (Phase 1 = [EURUSD, GBPUSD] solo).
     - `order_lib.sizing_for_profile('fotmarkets', entry, sl, capital_from_phase_progress)` → qty/risk.
     - Recuerda: ejecución MT5 manual. Watcher solo notifica trigger.
4. **Whitelist matrix check:** Llama `python3 -c "from pending_lib import
   load_all_pendings, apply_whitelist_matrix; ..."` con la orden candidata
   añadida virtualmente. Si la nueva orden quedaría en `suspended_policy` →
   preguntar al usuario: "Otra pending bloquea esta. ¿Abortar o cancelar la
   conflictiva?"
5. **Construye el order dict** usando `order_lib.build_order(...)` (ver paso 7).
6. **Preview ASCII + confirmación:**

   ```
   ╔══════════════════════════════════════╗
   ║  NEW ORDER [virtual, watcher-tracked]║
   ║  ID: ord_YYYYMMDD_HHMMSS_...         ║
   ║  Profile:  retail                    ║
   ║  Asset:    BTCUSDT.P LONG            ║
   ║  Entry:    77521  (tol 0.1%)         ║
   ║  SL:       77101  (-0.54%)           ║
   ║  TP1/2/3:  78571 / 79201 / 80041     ║
   ║  Qty:      0.00086 BTC (Margin $6.72)║
   ║  Risk:     $0.36 (2.0% de $18.09)    ║
   ║  TTL:      6h (expires 16:48 MX)     ║
   ║  Invalid:  76900 (below)             ║
   ║  Filters:  RSI<35, BB-lo, DC-lo,     ║
   ║            candle green (at trigger) ║
   ╚══════════════════════════════════════╝
   ```

   Espera respuesta literal `YES`. Cualquier otro valor → abort.

7. **Si YES:**
   - Llama `python3 -c "from order_lib import create_and_persist; create_and_persist(...)"`
     con los params parseados.
   - Imprime confirmación + `notify_hub.notify(Urgency.INFO, "order_created", ...)`
   - Recuerda al usuario: "Puedes `/watch` ahora para forzar primer tick, o esperar el launchd hourly."

8. **Flags opcionales:**
   - `--real` en retail → en v1 imprime **"⚠️ --real no implementado en v1, orden creada solo virtual"** y continúa con flow virtual.
   - `--check-regime` → en la orden set `check_regime_change: true`.

Si algún paso falla (guardian, whitelist, confirmación != YES) → NO escribe pending_orders.json.
