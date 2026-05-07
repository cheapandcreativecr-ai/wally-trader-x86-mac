---
name: polymarket-research
description: Corre research pipeline (H1-H4) sobre snapshots históricos y BTC OHLCV.
  Output markdown a docs/polymarket_research/.
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
<!-- generated from system/commands/polymarket-research.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /polymarket-research -->

<!-- args: [H1|H2|H3|H4|all] default all -->

Pasos que ejecuta Claude:

1. **Determinar hipótesis a correr:**
   - `$ARGUMENTS` vacío o `all` → todas (H1, H2, H3, H4)
   - `H1`/`H2`/`H3`/`H4` → solo esa

2. **Verificar prerequisitos:**
   - `.claude/scripts/polymarket/data/snapshots.jsonl` debe existir y tener >50 líneas
   - BTC OHLCV CSV debe estar disponible en `scripts/ml_system/data/BTCUSDT_15m_60d.csv` o equivalente
   - Si falta data → mensaje claro + abort

3. **Generar reporte markdown**:
   ```bash
   mkdir -p docs/polymarket_research
   .claude/scripts/.venv/bin/python -m polymarket.research.report \
     --out "docs/polymarket_research/$(date +%Y-%m-%d)-report.md"
   ```

4. **Mostrar al usuario:**
   - Path del reporte generado
   - Caveat si N<200 (incluido por el renderer)
   - Sugerencia: "Si IC en H4 cambió >0.1 vs último report, actualizar weights en `polymarket/config.py`."

5. **Si `$ARGUMENTS` es una hipótesis específica**, sólo correr ese helper y emitir su sección.

$ARGUMENTS
