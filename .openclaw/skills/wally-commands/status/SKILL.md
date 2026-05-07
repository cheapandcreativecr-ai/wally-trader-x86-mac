---
name: status
description: 'Wally Trader command: /status'
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
<!-- generated from system/commands/status.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /status -->

Muestra el estado completo del sistema según el profile activo.

Pasos que ejecuta Claude:

1. Lee profile activo: `PROFILE=$(python3 .claude/scripts/profile.py get)`

2. SI profile == "retail":
   - Lee `.claude/profiles/retail/config.md` (capital, estrategia activa)
   - Lee `.claude/profiles/retail/memory/trading_log.md` (últimos trades)
   - Lee `.claude/profiles/retail/memory/market_regime.md` (niveles vigentes)
   - Muestra statusline retail expandido:
     ```
     [RETAIL $13.63]
     Estrategia: Mean Reversion 15m
     Régimen: <detecta vía regime-detector rápido o cachea>
     Hora CR: HH:MM
     Trades hoy: 0/3
     Último trade: <fecha> <resultado>
     ```

3. SI profile == "ftmo":
   - Invoca: `python3 .claude/scripts/guardian.py --profile ftmo --action status`
   - Lee `.claude/profiles/ftmo/memory/challenge_progress.md`
   - Muestra statusline FTMO expandido:
     ```
     [FTMO $10k]
     Equity: $X (+Y%)
     Daily PnL: $X (Y% / 3% limit)
     Trailing DD: $X (Y% / 10% limit)
     Best Day ratio: Y% (cap 50%)
     Trades hoy: N/2
     Estrategia: FTMO-Conservative
     Asset vigilancia: <top 1-2 del morning-analyst-ftmo>
     ```

4. SI profile == "fotmarkets":
   - Lee `.claude/profiles/fotmarkets/memory/phase_progress.md` (capital + fase)
   - Lee `.claude/profiles/fotmarkets/memory/trading_log.md` (trades hoy)
   - Invoca: `python3 .claude/scripts/fotmarkets_phase.py detail`
   - Invoca: `python3 .claude/scripts/fotmarkets_guard.py check` (captura PASS/BLOCK)
   - Muestra statusline fotmarkets expandido:
     ```
     [FOTMARKETS $30.00]
     Fase: 1 (rango [0, 100))
     Próximo threshold: $100 (desbloquea USDJPY, XAUUSD, NAS100)
     Risk por trade: 10% ($3.00)
     Max trades hoy: 1
     Estrategia: Fotmarkets-Micro
     Ventana CR: 07:00–11:00
     Guardian: PASS/BLOCK <razón>
     Trades hoy: 0/1
     Último trade: <fecha> <resultado>
     ```

5. SI profile no reconocido:
   - Muestra warning: "Profile desconocido: <X>. Corre /profile ftmo|retail|fotmarkets."

6. Al final de cualquier output, incluye: "Última actualización: <timestamp>. Cambiar profile: /profile ftmo|retail|fotmarkets"

## Sección Watcher (v1)

Al final del output de `/status`, añade:

```bash
# Read watcher status + pending summary
python3 <<'EOF'
import json
from pathlib import Path
from pending_lib import load_all_pendings, PROFILES, TERMINAL_STATUSES

status_path = Path(".claude/watcher/status.json")
if status_path.exists():
    s = json.loads(status_path.read_text())
    print(f"\n## Watcher")
    print(f"Last tick: {s.get('last_tick_utc','-')} ({s.get('duration_ms','?')}ms, ok={not s.get('errors')})")
    print(f"Pendings checked last tick: {s.get('pendings_checked', 0)}")
    actions = s.get('actions', [])
    by_action = {}
    for a in actions:
        by_action[a.get('action','?')] = by_action.get(a.get('action','?'), 0) + 1
    if by_action:
        parts = " | ".join(f"{k}: {v}" for k,v in by_action.items())
        print(f"Actions: {parts}")
    if s.get('errors'):
        print("Errors:")
        for e in s['errors']:
            print(f"  • {e}")
    print(f"Next tick ETA: {s.get('next_tick_eta_utc','-')}")
else:
    print("\n## Watcher\n_(no tick run yet — instala launchd o corre /watch)_")

# Pending counts per profile
all_p = load_all_pendings()
print("\n### Pendings por profile")
for profile, orders in all_p.items():
    active = [o for o in orders if o.get('status') not in TERMINAL_STATUSES]
    if active:
        print(f"  {profile}: {len(active)} active")
EOF
```
