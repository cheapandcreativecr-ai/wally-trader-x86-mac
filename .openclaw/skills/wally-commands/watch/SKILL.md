---
name: watch
description: 'Wally Trader command: /watch'
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
<!-- generated from system/commands/watch.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /watch -->

Fuerza un tick manual del watcher (no espera al próximo launchd).

Uso: `/watch` (sin args)

Pasos:

1. Ejecuta:
   ```bash
   cd /Users/josecampos/Documents/wally-trader
   python3 .claude/scripts/watcher_tick.py
   ```
2. Lee `.claude/watcher/dashboard.md` y muéstralo al usuario.
3. Lee `.claude/watcher/status.json` y resume en 3 líneas:
   - "Last tick: <utc> (<ms>ms, ok=<bool>)"
   - "Pendings checked: N | errors: M"
   - "Actions: heartbeat(X) / escalated(Y) / invalidated(Z)"
4. Si hay `errors` → imprímelos.
5. Si hay `action=escalated` → recuérdale al usuario: "Claude-headless validando <id>, notif CRITICAL si 4/4 filtros."

NO preguntas al usuario; es read + run + display.
