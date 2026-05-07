---
name: profile
description: 'Wally Trader command: /profile'
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
<!-- generated from system/commands/profile.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /profile -->

# /profile

Muestra o cambia el profile activo del sistema.

Uso:
- `/profile` — muestra profile activo y timestamp
- `/profile ftmo` — switch a FTMO
- `/profile retail` — switch a retail
- `/profile fotmarkets` — switch a Fotmarkets (bonus $30)
- `/profile status` — resumen rápido de los 3 profiles

Pasos que ejecuta Claude:

1. Si el argumento es vacío:
   - Corre `python3 .claude/scripts/profile.py show`
   - Devuelve el profile actual + timestamp

2. Si el argumento es `status`:
   - Lee `.claude/profiles/retail/config.md` y resume (capital, strategy)
   - Lee `.claude/profiles/ftmo/config.md` y resume (challenge progress)
   - Lee `.claude/profiles/fotmarkets/config.md` y resume (capital, fase)
   - Si FTMO tiene `equity_curve.csv` no vacío, muestra equity + daily PnL
   - Si FOTMARKETS tiene `phase_progress.md` poblado, muestra capital + fase
   - Marca con ▶ el profile activo

3. Si el argumento es `ftmo`, `retail` o `fotmarkets`:
   - **Validación previa**: pregunta "¿tienes trade abierto en el profile actual?" — si sí, BLOCK switch con mensaje "cierra primero"
   - Corre `python3 .claude/scripts/profile.py set <arg>`
   - Confirma con el nuevo statusline
   - Si destino es `ftmo`: prompt "¿actualizar equity FTMO ahora? (último: $X @ <timestamp>)"
   - Si destino es `fotmarkets`: prompt "¿ya leíste bonus T&C? Ver memory/session_notes.md"

4. Si el argumento no es reconocido:
   - Devuelve error: "uso: /profile [ftmo|retail|fotmarkets|status]"

Reglas:
- NUNCA cambiar profile si hay trade abierto (evita cross-contamination)
- Después de switch, recordar al usuario que las memorias del otro profile quedan intactas

### Pre-switch: pending handshake (v1 watcher)

Antes de cambiar de profile, checkear pending orders activas:

1. **Leer pending del profile actual:**
   ```bash
   python3 -c "
   from pending_lib import load_pendings, TERMINAL_STATUSES
   orders = [o for o in load_pendings('$CURRENT_PROFILE') if o.get('status') not in TERMINAL_STATUSES and o.get('status') != 'suspended_profile_switch']
   for o in orders:
       print(f'{o[\"id\"]}|{o[\"asset\"]}|{o.get(\"side\",\"\")}|{o[\"status\"]}|dist_ttl={o[\"expires_at\"]}')
   "
   ```

2. Si el output tiene líneas → mostrar prompt:
   ```
   ⚠️ Profile actual `<current>` tiene <N> pending activa(s):
     • ord_xxx BTCUSDT.P LONG (status: pending, TTL ...)

   Al cambiar a `<target>`, ¿qué hago?
     [s] suspend — mantener pending pero pausar watcher (volver reactiva)
     [c] cancel — marcar canceled_manual (terminal, no vuelve)
     [k] keep_active — dejar watcher vigilándolas (respeta matriz whitelist)

   Tu elección:
   ```

3. Aplicar elección:
   - `s` → update_status a `suspended_profile_switch` para cada pending.
   - `c` → update_status a `canceled_manual`.
   - `k` → no tocar (default fallback si timeout/unclear input).

4. **Leer pending suspended del profile target:**
   ```bash
   python3 -c "
   from pending_lib import load_pendings
   orders = [o for o in load_pendings('$TARGET_PROFILE') if o.get('status') == 'suspended_profile_switch']
   for o in orders:
       print(f'{o[\"id\"]}|{o[\"asset\"]}|{o.get(\"side\",\"\")}|ttl={o[\"expires_at\"]}')
   "
   ```

5. Si hay suspended → mostrar prompt Caso B:
   ```
   ℹ️ Profile target `<target>` tiene <N> pending suspended:
     • ord_zzz ...

   ¿Reactivar o descartar?
     [r] reopen — status=pending (watcher vigila de nuevo; si TTL expiró, pasa a expired_ttl en siguiente tick)
     [d] discard — marcar canceled_manual
   ```

6. Aplicar elección. Para `reopen`: update_status a `pending`.

7. **Seguir con el set profile existente** (`python3 .claude/scripts/profile.py set <target>`).

8. Al final, disparar un `/watch` tick (o llamar directo `python3 .claude/scripts/watcher_tick.py`)
   para refresh del dashboard con el nuevo estado.
