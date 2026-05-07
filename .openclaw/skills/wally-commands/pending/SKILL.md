---
name: pending
description: 'Wally Trader command: /pending'
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
<!-- generated from system/commands/pending.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /pending -->

# /pending command

Lista, muestra o modifica pending orders virtuales.

## Uso

- `/pending` — lista pending del profile activo (active + suspended)
- `/pending all` — lista cross-profile
- `/pending show <id>` — detalle completo con status_history
- `/pending cancel <id>` — marca `canceled_manual` (terminal, no-op después)
- `/pending modify <id> <field>=<val>` — edit limitado:
   campos permitidos: `tp1`, `tp2`, `tp3`, `ttl_hours`, `invalidation_price`, `check_regime_change`

## Implementación

### Parsing y despacho

```bash
#!/bin/bash
set -euo pipefail

PROFILE="${WALLY_PROFILE:-retail}"
REPO_ROOT="/Users/josecampos/Documents/wally-trader"
cd "$REPO_ROOT"

# Parse subcommand
SUBCOMMAND="${1:-}"
ID="${2:-}"
FIELDVAL="${3:-}"

case "$SUBCOMMAND" in
  ""|all|show|cancel|modify)
    ;;
  *)
    echo "Unknown subcommand: $SUBCOMMAND"
    exit 1
    ;;
esac
```

### List (profile activo o all)

```bash
if [ -z "$SUBCOMMAND" ] || [ "$SUBCOMMAND" = "all" ]; then
  python3 -c "
from pending_lib import load_all_pendings, PROFILES
all_p = load_all_pendings()
for profile, orders in all_p.items():
    if not orders: 
        print(f'{profile}: (empty)')
        continue
    print(f'\n{profile}:')
    for o in orders:
        status = o.get('status', '?')
        asset = o.get('asset', '?')
        side = o.get('side', '?')
        entry = o.get('entry', '-')
        print(f'  {o[\"id\"]:<15}  {asset:<10} {side:<5}  entry={entry:<8}  status={status}')
  "
  exit 0
fi
```

### Show <id>

```bash
if [ "$SUBCOMMAND" = "show" ]; then
  [ -z "$ID" ] && { echo "Usage: /pending show <id>"; exit 1; }
  python3 -c "
from pending_lib import find_by_id
import json
result = find_by_id('$ID')
if result is None:
    print(f'Order {\"$ID\"} not found.')
    exit(1)
profile, order = result
print(f'Profile: {profile}')
print(json.dumps(order, indent=2))
  "
  exit $?
fi
```

### Cancel <id>

```bash
if [ "$SUBCOMMAND" = "cancel" ]; then
  [ -z "$ID" ] && { echo "Usage: /pending cancel <id>"; exit 1; }
  
  # Confirmation
  read -p "Cancel $ID? This is terminal. [YES/no] " -r confirm
  if [ "$confirm" != "YES" ]; then
    echo "Canceled."
    exit 0
  fi
  
  python3 -c "
from pending_lib import find_by_id, update_status
result = find_by_id('$ID')
if result is None:
    print(f'Order {\"$ID\"} not found.')
    exit(1)
profile, _ = result
update_status(profile, '$ID', 'canceled_manual', note='user /pending cancel')
print('Order canceled.')
  "
  exit $?
fi
```

### Modify <id> <field>=<val>

```bash
if [ "$SUBCOMMAND" = "modify" ]; then
  [ -z "$ID" ] && { echo "Usage: /pending modify <id> <field>=<val>"; exit 1; }
  [ -z "$FIELDVAL" ] && { echo "Usage: /pending modify <id> <field>=<val>"; exit 1; }
  
  FIELD="${FIELDVAL%%=*}"
  VAL="${FIELDVAL#*=}"
  
  # Whitelist
  case "$FIELD" in
    tp1|tp2|tp3|ttl_hours|invalidation_price|check_regime_change)
      ;;
    *)
      echo "Field not allowed: $FIELD. Allowlist: tp1 tp2 tp3 ttl_hours invalidation_price check_regime_change"
      exit 1
      ;;
  esac
  
  python3 -c "
from pending_lib import find_by_id, load_pendings, save_pendings
from datetime import datetime, timedelta
result = find_by_id('$ID')
if result is None:
    print(f'Order {\"$ID\"} not found.')
    exit(1)
profile, _ = result

# Check if terminal status
p = [x for x in load_pendings(profile) if x['id'] == '$ID'][0]
terminal_statuses = ['canceled_manual', 'filled', 'expired_ttl', 'expired_regime', 'hit_sl', 'hit_tp']
if p['status'] in terminal_statuses:
    print(f'Cannot modify terminal order (status={p[\"status\"]})')
    exit(1)

pendings = load_pendings(profile)
for p in pendings:
    if p['id'] == '$ID':
        if '$FIELD' == 'ttl_hours':
            base = datetime.fromisoformat(p['created_at'])
            p['expires_at'] = (base + timedelta(hours=float('$VAL'))).isoformat(timespec='seconds')
        elif '$FIELD' == 'check_regime_change':
            p['check_regime_change'] = ('$VAL'.lower() == 'true')
        else:
            p['$FIELD'] = float('$VAL')
        
        p.setdefault('status_history', []).append({
            'at': datetime.now().astimezone().isoformat(timespec='seconds'),
            'status': p['status'],
            'note': 'modify $FIELD=$VAL'
        })
        break

save_pendings(profile, pendings)
print('Modified.')
  "
  
  # Re-render dashboard
  python3 .claude/scripts/watcher_tick.py --dry-run 2>/dev/null || true
  exit 0
fi
```

## Notes

- El profile activo está en `$WALLY_PROFILE` (default: `retail`)
- Funciones usadas: `load_all_pendings()`, `load_pendings()`, `find_by_id()`, `update_status()`, `save_pendings()`
- Terminal statuses: `canceled_manual`, `filled`, `expired_ttl`, `expired_regime`, `hit_sl`, `hit_tp`
