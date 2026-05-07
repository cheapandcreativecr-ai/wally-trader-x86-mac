---
name: neptune
description: Lee outputs actuales de los indicadores Neptune (si cargados en chart)
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
<!-- generated from system/commands/neptune.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /neptune -->


Lee los outputs actuales de los indicadores Neptune cargados en el chart y da interpretación.

## Qué hace

1. `chart_get_state` → verifica qué Neptune indicators están activos
2. `data_get_study_values` → lee valores actuales (Hyper Wave, Neptune Line, etc.)
3. `data_get_pine_boxes study_filter="Neptune - SMC"` → Order Blocks activos
4. `data_get_pine_labels study_filter="Neptune"` → eventos estructurales
5. `data_get_pine_lines study_filter="Neptune"` → niveles dibujados
6. Interpreta cada output según la lógica documentada en `.claude/skills/neptune-indicators/SKILL.md`

## Output format

```
🔷 NEPTUNE READINGS — [símbolo] [TF]

Indicadores activos: [lista]

═ Neptune Signals™ ═
- Neptune Line: [precio]
- Precio actual vs línea: ↑/↓ [diferencia %]
- Shapes activos: [sí/no]
- Sesgo: BULLISH/BEARISH

═ Neptune Oscillator™ ═
- Hyper Wave: [valor] [zona: oversold/neutral/overbought]
- Hyper Wave MA: [valor]
- Cruce: [arriba/abajo/neutral]
- Directional Pressure: [valor] [presión compradora/vendedora/neutral]

═ Neptune SMC™ ═ (si activo)
- Order Blocks cercanos: [lista con precios]
- FVGs no rellenados: [lista]
- BSL/SSL: [niveles]

═ Neptune Money Flow Profile™ ═ (si activo)
- POC: [precio]
- VAH: [precio] | VAL: [precio]

═ VEREDICTO NEPTUNE ═
Sesgo general: [LONG / SHORT / NEUTRAL]
Confluencia interna: [X/Y indicadores alineados]
Próxima zona clave: [precio]
```

Si no hay Neptune cargado: "No hay indicadores Neptune activos en el chart. Agrégalos desde Indicadores > Neptune — Signals / Oscillator / SMC."
