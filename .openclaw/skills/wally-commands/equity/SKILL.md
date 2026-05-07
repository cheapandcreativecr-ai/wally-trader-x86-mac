---
name: equity
description: 'Wally Trader command: /equity'
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
<!-- generated from system/commands/equity.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /equity -->

Actualiza el equity actual del profile FTMO o FundingPips (no aplica a retail).

Uso:
- `/equity <valor>` — registra nuevo equity en USD
- `/equity <valor> "<nota>"` — con nota descriptiva opcional
- `/equity` (sin arg) — muestra último equity conocido

Pasos que ejecuta Claude:

1. Lee profile activo: `python3 .claude/scripts/profile.py get`

2. Si profile == "retail" o "retail-bingx" o "fotmarkets":
   - Mensaje: "/equity solo aplica a profiles ftmo y fundingpips. Profile activo: <X>."
   - NO ejecutar

3. Si profile == "fundingpips":
   - Si sin argumentos: lee última línea de `.claude/profiles/fundingpips/memory/equity_curve.csv`
   - Si hay valor: append al CSV con timestamp + recalcula daily_pnl_pct + total_dd_pct
   - Calcula y muestra:
     - Equity actual: $X (vs initial $10,000 = +/-N.NN%)
     - Total DD: N.NN% (BLOCK en -3%, oficial -5%)
     - Daily PnL: N.NN% (BLOCK en -2%, oficial -3%)
     - Trades hoy: N/2
     - Días operados: N/7 mínimo
   - Si total DD ≤ -3% → ⚠️ "BLOCK threshold alcanzado, NO operar más hoy"
   - Si daily PnL ≤ -2% → ⚠️ "Daily BLOCK alcanzado, force close si hay open"

3. Si sin argumentos:
   - Lee última línea de `.claude/profiles/ftmo/memory/equity_curve.csv`
   - Muestra: "Último equity: $X @ YYYY-MM-DDThh:mm (source, nota)"
   - Si curve vacío: "Sin actualizaciones. Initial: $10,000"

4. Si hay argumento numérico:
   - Valida que es número positivo razonable (entre 1000 y 50000)
   - Ejecuta: `python3 .claude/scripts/guardian.py --profile ftmo --action equity-update --value <valor> [--note "<nota>"]`
   - Devuelve: JSON del update + recalcula status
   - Ejecuta: `python3 .claude/scripts/guardian.py --profile ftmo --action status` y muestra formateado:
     - Equity actual: $X (+N.NN%)
     - Daily PnL: $X (N.NN% / 3% limit)
     - Trailing DD: $X (N.NN% / 10% limit)
     - Best Day ratio: N% (cap 50%)

5. Si el valor sube contra peak anterior → nota visual: "🎯 Nuevo peak!"

6. Si el valor cruza algún threshold peligroso → aviso en rojo:
   - daily_pnl_pct <= -2.5% → "⚠️ 2.5% daily loss, cerca del 3% limit"
   - trailing_dd_pct >= 8.0% → "⚠️ Trailing DD 80% del límite"
   - best_day_ratio >= 0.45 → "ℹ️ Best day cerca del cap 50%"
