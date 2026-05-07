---
name: review
description: Review semanal / mensual de performance
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
<!-- generated from system/commands/review.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /review -->


Invoca el agente `journal-keeper` para hacer un review completo.

Default: review última semana.

Argumentos aceptados:
- "semanal" (default)
- "mensual"
- "ultimos 7 dias"
- "ultimos 30 dias"
- fecha específica "review desde 2026-04-15"

Devuelve:
- **Métricas:** WR, PF, avg win/loss, max DD, total trades
- **Patrones:** mejores días, mejores horas, setups que funcionan
- **Disciplina:** % trades con 4/4 filtros, hora respetada
- **Capital:** curva + delta %
- **Vs targets:** cumples WR≥60% PF≥1.8 DD≤15%?
- **1 cambio** específico para siguiente período
- **Objetivo** cuantificable próximo período

Período a revisar:
$ARGUMENTS
