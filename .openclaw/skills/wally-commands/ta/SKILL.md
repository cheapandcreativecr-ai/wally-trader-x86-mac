---
name: ta
description: Análisis técnico avanzado con 5 metodologías (ICT, armónicos, chartismo,
  Elliott, Fibonacci)
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
<!-- generated from system/commands/ta.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /ta -->


Invoca el agente `technical-analyst` para análisis profundo con las 5 metodologías avanzadas:

1. **Smart Money Concepts (ICT)** — Order Blocks, FVG, liquidity, BoS/ChoCh
2. **Patrones Armónicos** — Gartley, Bat, Butterfly, Crab, Shark, Cypher
3. **Chartismo Clásico** — H&S, triangles, flags, wedges, double tops
4. **Ondas de Elliott** — wave count en TFs múltiples
5. **Fibonacci** — retracements, extensions, confluencia MTF

Devuelve:
- Contexto multi-TF (1D, 4H, 1H, 15m)
- Análisis por cada metodología
- CONFLUENCIAS identificadas (cuando varias apuntan al mismo lugar)
- Setup propuesto con size modifier según cantidad de confluencias
- Niveles exactos (Entry, SL, TP1/2/3)

Timeframe y enfoque específico (opcional):
$ARGUMENTS

Ejemplos:
- `/ta` → análisis completo multi-TF
- `/ta smart money` → solo ICT en foco
- `/ta armonico gartley` → buscar patrones armónicos específicos
- `/ta fibonacci 1h` → solo fib en 1H
- `/ta elliot` → wave count y proyecciones
- `/ta confluencia` → reporte de confluencias entre todas las metodologías
