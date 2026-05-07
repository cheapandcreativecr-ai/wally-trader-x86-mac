---
name: filled
description: 'Wally Trader command: /filled'
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
<!-- generated from system/commands/filled.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /filled -->

# /filled command

Marca una pending order como ejecutada en el exchange/MT5 (llamado después de
ejecutar manual tras notif `triggered_go`).

## Uso

- `/filled <id>` — usa entry del pending como fill price
- `/filled <id> price=77498` — override con slippage real

## Implementación

### Parsing y validación

```bash
#!/bin/bash
set -euo pipefail

PROFILE="${WALLY_PROFILE:-retail}"
REPO_ROOT="/Users/josecampos/Documents/wally-trader"
cd "$REPO_ROOT"

ID="${1:-}"
PRICE_OVERRIDE="${2:-}"

if [ -z "$ID" ]; then
    echo "Usage: /filled <id> [price=X]"
    exit 1
fi

# Extract price if provided
FILL_PRICE=""
if [ -n "$PRICE_OVERRIDE" ]; then
    if [[ "$PRICE_OVERRIDE" == price=* ]]; then
        FILL_PRICE="${PRICE_OVERRIDE#price=}"
    else
        echo "Invalid format: use 'price=X' for override"
        exit 1
    fi
fi
```

### Step 1: Find order and capture profile

```bash
RESULT=$(python3 -c "
from pending_lib import find_by_id
import json
result = find_by_id('$ID')
if result:
    profile, order = result
    print(json.dumps({'profile': profile, 'order': order}))
else:
    print('')
")

if [ -z "$RESULT" ]; then
    echo "ERROR: Order '$ID' not found"
    exit 1
fi

PROFILE=$(echo "$RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin)['profile'])")
ORDER=$(echo "$RESULT" | python3 -c "import sys, json; d = json.load(sys.stdin); print(json.dumps(d['order']))")
```

### Step 2: Check status (warn if not triggered_go, but continue)

```bash
STATUS=$(echo "$ORDER" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', '?'))")

if [ "$STATUS" != "triggered_go" ]; then
    echo "⚠️  WARNING: Order status is '$STATUS' (expected 'triggered_go')"
    echo "   Continuing anyway (user knows what they do)"
fi
```

### Step 3: Determine fill price

```bash
# If override provided, use it. Otherwise use entry.
if [ -z "$FILL_PRICE" ]; then
    FILL_PRICE=$(echo "$ORDER" | python3 -c "import sys, json; print(json.load(sys.stdin)['entry'])")
fi

ASSET=$(echo "$ORDER" | python3 -c "import sys, json; print(json.load(sys.stdin)['asset'])")
SIDE=$(echo "$ORDER" | python3 -c "import sys, json; print(json.load(sys.stdin)['side'])")
SL=$(echo "$ORDER" | python3 -c "import sys, json; print(json.load(sys.stdin)['sl'])")
TP1=$(echo "$ORDER" | python3 -c "import sys, json; print(json.load(sys.stdin).get('tp1', '-'))")
RISK_USD=$(echo "$ORDER" | python3 -c "import sys, json; print(json.load(sys.stdin).get('risk_usd', 0))")
RISK_PCT=$(echo "$ORDER" | python3 -c "import sys, json; print(json.load(sys.stdin).get('risk_pct', 0))")
```

### Step 4: Update status to 'filled'

```bash
python3 -c "
from pending_lib import update_status
update_status('$PROFILE', '$ID', 'filled', 
              note='filled via /filled at \$FILL_PRICE')
"

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to update order status"
    exit 1
fi
```

### Step 5: Append to trading_log.md

```bash
LOG_FILE="./.claude/profiles/$PROFILE/trading_log.md"

if [ ! -f "$LOG_FILE" ]; then
    mkdir -p "./.claude/profiles/$PROFILE"
    touch "$LOG_FILE"
fi

# Get current date
DATE=$(date +"%Y-%m-%d")

# Append trade filled entry
python3 -c "
import os
from datetime import datetime

log_path = '$LOG_FILE'
date_str = '$DATE'

# Read existing log
with open(log_path, 'r') as f:
    content = f.read()

# Check if date header exists
date_header = f'## {date_str}'
if date_header not in content:
    # Add date header at end
    if content and not content.endswith('\n\n'):
        content += '\n'
    content += f'\n## {date_str}\n'

# Append trade entry
trade_entry = f'''Trade filled: $ID | $ASSET $SIDE | entry \${FILL_PRICE} | SL \${SL} | TP \${TP1}
Risk: \${RISK_USD} ({RISK_PCT}%)
Source: /order + /filled (virtual-tracked watcher)

'''

with open(log_path, 'a') as f:
    f.write(trade_entry)
"
```

### Step 6: Notify INFO

```bash
python3 -c "
from notify_hub import notify, Urgency
notify(Urgency.INFO, 'filled', {
    'order_id': '$ID',
    'profile': '$PROFILE',
    'asset': '$ASSET',
    'side': '$SIDE',
    'fill_price': float('$FILL_PRICE'),
    'sl': float('$SL'),
    'tp1': float('$TP1'),
    'risk_usd': float('$RISK_USD'),
    'risk_pct': float('$RISK_PCT'),
})
"
```

### Step 7: Output ASCII confirmation box

```bash
cat << EOF
┌────────────────────────────────────────────────────────┐
│ ✓ Order Filled                                         │
├────────────────────────────────────────────────────────┤
│ ID:          $ID                                       │
│ Profile:     $PROFILE                                  │
│ Asset:       $ASSET                                    │
│ Side:        $SIDE                                     │
│ Fill Price:  $FILL_PRICE                               │
│ SL:          $SL                                        │
│ TP1:         $TP1                                       │
│ Risk:        \$$RISK_USD ($RISK_PCT%)                  │
│ Status:      filled                                    │
└────────────────────────────────────────────────────────┘
EOF
```

## Notes

- El profile activo está en `$WALLY_PROFILE` (default: `retail`)
- Si status != `triggered_go`, se muestra warning pero se continúa (user override)
- Fill price por defecto es la entry del order; override con `price=X`
- Append al log preserva el schema existente (fecha + trade + risk + source)
- Notificación se envía con Urgency.INFO via `notify_hub`
- Terminal statuses: `canceled_manual`, `filled`, `expired_ttl`, `expired_regime`, `hit_sl`, `hit_tp`
