---
name: polymarket
description: Macro sentiment desde Polymarket (Fed/recession/tariffs). Composite -100..+100
  + tabla markets. 5° filtro, nunca gate.
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
<!-- generated from system/commands/polymarket.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /polymarket -->

<!-- args: [fed|movers|history <slug>] opcional -->

Pasos que ejecuta Claude:

1. **Correr el analyzer** y leer el JSON:
   ```bash
   .claude/scripts/.venv/bin/python -m polymarket.analyzer --json
   ```

2. **Si `status != "FRESH"`** → mostrar al usuario:
   ```
   ⚠️ PM Macro: <STALE|NO_DATA|NO_MARKETS> — no disponible esta sesión.
   Última snapshot hace <N> min. Verificar `launchctl list | grep polymarket`.
   ```
   Y terminar.

3. **Si hay argumento `fed`** → filtrar markets cuyo slug contiene "fed".
   **Si hay argumento `movers`** → solo markets con `abs(delta_24h) > 0.05`.
   **Si hay argumento `history <slug>`** → leer snapshots para ese slug y mostrar línea de tiempo ASCII (mejor esfuerzo: 7 días, 1 char por punto).

4. **Render quick-summary 3 líneas + tabla completa** según formato de la skill `polymarket-macro`:
   ```
   🟢 PM Macro Bias: +13.7 (MILD-BULL) | 11 markets | last poll 18min ago
   ⚠️ Fed-cut +14pp en 7d → DXY bajista esperado
   ✅ Recession odds -5pp → risk-on alineado

   ### Markets relevantes
   | Market | Prob | Δ24h | Δ7d | Contribución |
   |---|---|---|---|---|
   | ...
   ```

5. **Recordatorio final** (siempre):
   ```
   ⚠️ PM Macro es 5° filtro. NO convierte un NO-GO técnico en GO.
   ```

$ARGUMENTS
