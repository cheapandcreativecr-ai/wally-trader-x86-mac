---
name: equity-curve
description: ASCII chart de la equity curve del profile activo (lectura visual rápida
  en terminal)
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
<!-- generated from system/commands/equity-curve.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /equity-curve -->

<!-- args: [--days N] (default 30) -->

# /equity-curve

Renderiza un ASCII chart de la equity curve del profile activo. Útil para ver visualmente el progreso sin abrir un editor externo.

## Steps

1. Lee profile activo: `PROFILE=$(python3 .claude/scripts/profile.py get)`

2. Localiza equity_curve.csv del profile:
   - retail / retail-bingx: derivado de trading_log.md (calculado on-the-fly)
   - ftmo / fundingpips: `.claude/profiles/<profile>/memory/equity_curve.csv`
   - bitunix: `.claude/profiles/bitunix/memory/equity_curve.csv`
   - quantfury: `.claude/profiles/quantfury/memory/equity_curve.csv` (en BTC)

3. Parse últimos N días (default 30, configurable con `--days N`).

4. Render ASCII chart con altura 15 líneas, width 60 caracteres, eje Y normalizado.
   Format:
   ```
   $X.XX (peak)  ┤                ╭──╮
                 ┤             ╭──╯  ╰─╮
                 ┤           ╭─╯       ╰╮     ╭───
                 ┤   ╭──────╯           ╰─────╯
   $X.XX (start) ┤───╯
                 └────────────────────────────────
                 day 1                        day 30
   
   Stats: +X.X% over 30d | Max DD: -X.X% | Sharpe: X.XX
   ```

5. Stats footer con: total return %, max drawdown %, Sharpe annualized, # trades.

## Notas

- Si profile NO tiene equity_curve trackeada → mensaje: "Equity curve no trackeada en {profile}. Setup `/equity` first o ver `journal.md`"
- Quantfury muestra valores en BTC absoluto + comparison vs HODL (same chart)
- ASCII chart usa caracteres unicode `╭ ╰ ─ │` — funciona en macOS/Linux/Windows Terminal con UTF-8

## Implementación (helper)

```bash
python3 .claude/scripts/equity_curve_ascii.py --profile $PROFILE --days ${DAYS:-30}
```

(El helper se crea on-demand. Si no existe, mostrar mensaje "Helper no implementado aún. PR welcome.")
