---
name: risk-var
description: Position sizing basado en VaR/CVaR histórico (más adaptativo que flat
  2%, se ajusta cuando ATR explota).
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
<!-- generated from system/commands/risk-var.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /risk-var -->


Pasos que ejecuta Claude:

1. **Detectar profile activo:**
   ```bash
   PROFILE=$(python3 .claude/scripts/profile.py get)
   ```
   Capital según profile:
   - `retail` → leer `Capital actual: $X.XX` de trading_log.md (default $18.09)
   - `retail-bingx` → $0.93
   - `ftmo` → $10,000 (o leer equity_curve.csv)
   - `fotmarkets` → leer `phase_progress.md` capital_current

2. **Pull bars 1H del símbolo activo:**
   ```
   mcp__tradingview__chart_set_timeframe 60
   mcp__tradingview__data_get_ohlcv summary=false limit=200
   ```
   Guardar a `/tmp/bars1h.json`.

3. **Llamar al helper:**
   ```bash
   python3 .claude/scripts/risk_var.py \
     --bars-file /tmp/bars1h.json \
     --capital <CAPITAL> \
     --leverage 10 \
     --target-var-pct 1.5 \
     --confidence 95
   ```

4. **Interpretar output:**
   - **Notional max** → cuánto USD posicionar
   - **Margin used** → cuánto del capital se usa como margen (con leverage)
   - **VaR comparison vs flat-2%** → comunicar si es más/menos conservador

5. **Comparar con `/risk` tradicional:**
   - Si VaR-based size es <80% del flat-2% → recomendar el VaR (mejor protección en alta vol)
   - Si VaR es >120% del flat-2% → usar el flat-2% (VaR es overly aggressive cuando vol es baja)
   - Si están dentro de ±20% → usar el VaR (más adaptativo)

6. **Reglas según profile:**
   - **retail/retail-bingx**: target-var-pct = 1.5%
   - **ftmo**: target-var-pct = 0.5% (FTMO 3% daily limit muy restrictivo)
   - **fotmarkets**: target-var-pct = phase-aware (10% / 5% / 2% según fase actual)

7. **Output al usuario:**
   Tabla con stats de retornos + sizing comparativo. Recomendación clara.

## Casos de uso

- **Pre-entry validation:** después de los 4 filtros, calcular size con VaR antes de ejecutar.
- **Post-FOMC/CPI:** cuando ATR explota, VaR detecta automáticamente y reduce size sin tener que cambiar reglas manualmente.
- **FTMO drawdown protection:** la regla "0.5% VaR" mantiene el daily loss bien lejos del 3% FTMO limit.

## Limitaciones

- VaR histórico asume que el pasado refleja el futuro. En cisne negro (FOMC sorpresa, fork) puede subestimar.
- Sample size <30 returns → VaR poco confiable. El helper avisa con stderr warning.
- No reemplaza al SL real. Es input adicional para sizing.

$ARGUMENTS
