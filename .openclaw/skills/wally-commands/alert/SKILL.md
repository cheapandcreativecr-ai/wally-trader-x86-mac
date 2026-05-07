---
name: alert
description: Configura una alerta manual con notificación macOS
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
<!-- generated from system/commands/alert.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /alert -->


Crea una alerta personalizada que te notifique cuando suceda algo específico.

Ejemplos de uso:
- `/alert precio 75500 long` → notifica cuando BTC alcance 75,500
- `/alert rsi 30` → notifica cuando RSI llegue a 30
- `/alert regime change` → notifica si el régimen cambia
- `/alert setup ready` → notifica cuando 4/4 filtros alineen

Mecánica:
1. Crea un script en background en `.claude/scripts/alert_$TIMESTAMP.sh`
2. Script monitorea la condición cada 60 segundos
3. Cuando se cumple → `osascript -e 'display notification ...'`
4. Se auto-mata después de notificar o a las 23:59 CR (fin de ventana operativa)

Alerta a configurar:
$ARGUMENTS
