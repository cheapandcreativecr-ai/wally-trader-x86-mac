---
name: chart
description: Limpia chart TradingView y redibuja niveles actuales
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
<!-- generated from system/commands/chart.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /chart -->


Invoca el agente `chart-drafter` para actualizar el chart de TradingView.

Acciones:
1. Limpiar TODOS los dibujos previos (via context menu workaround)
2. Calcular niveles actualizados:
   - Donchian(15) H/L
   - Bollinger Bands(20,2)
   - Zonas de entrada (±0.1%)
   - SL/TP1/TP2/TP3 para LONG y SHORT
3. Dibujar todo en chart con colores:
   - Naranja (Donchian High)
   - Cyan (Donchian Low)
   - Rojo dashed (SLs)
   - Verde (TPs)
   - Línea vertical naranja (cierre 23:59 CR — no dormir con posición)
4. Texto superior con resumen

Opciones (vía argumentos):
- "con niveles extra" → añade PDH/PDL, Weekly Open, VWAP
- "breakout" → dibuja setup de Donchian Breakout en vez de Mean Reversion

$ARGUMENTS
