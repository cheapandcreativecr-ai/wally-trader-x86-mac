---
name: pine-gen
description: Genera un indicador Pine Script v6 desde lenguaje natural y lo compila
  en TradingView
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
<!-- generated from system/commands/pine-gen.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /pine-gen -->


Genera un indicador **Pine Script v6** desde una descripción en lenguaje natural, lo guarda en `system/pine_library/`, y lo compila contra TradingView Desktop para verificar que no tiene errores.

Inspirado en el video YouTube "How to Connect Claude to TradingView (AI Indicators + Backtest)" que muestra el workflow `describe → generate → compile → backtest`.

## Uso

```
/pine-gen <descripción del indicador>
```

**Ejemplos:**
- `/pine-gen VWAP con bandas a 1σ y 2σ, color teal, alerta cuando price cruza 2σ`
- `/pine-gen Opening Range Breakout 30min sesión NY, dibuja high/low del rango y ATR-projected targets`
- `/pine-gen Bollinger Bands(20, 2) con squeeze detector cuando bandwidth < 0.5×ATR(14)`
- `/pine-gen Stochastic RSI con divergencia bullish/bearish auto-marked en pivots`

## Pasos

1. **Profile guard:** ninguno — `/pine-gen` funciona en cualquier profile (los indicadores son globales).

2. **Slug del indicador:** convertir descripción a un slug snake_case máximo 40 caracteres.
   ```
   "VWAP con bandas a 1σ y 2σ" → vwap_bands_1sigma_2sigma
   ```

3. **Generar Pine v6 código** siguiendo estas reglas estrictas:

   **REGLAS PINE v6:**
   - Versión obligatoria: `//@version=6` en línea 1
   - Indicator declaration: `indicator(title="<Nombre>", overlay=<true|false>, ...)`
   - Inputs visibles al usuario: usar `input.int()`, `input.float()`, `input.color()`, `input.bool()`, `input.timeframe()`
   - Plots: `plot()`, `plotshape()`, `plotchar()`, `plotcandle()`, `bgcolor()`, `hline()`
   - Variables persistentes: usar `var` para counters/state que sobrevive bars
   - Series vs simple: respetar el sistema de tipos de Pine 6 (no mezclar)
   - Strings/labels para alertas: `alert("mensaje", alert.freq_once_per_bar_close)`
   - Comentarios docstring al inicio explicando qué hace el indicador y por qué
   - **NO uses funciones deprecated de Pine v4/v5** (`study()`, `security()`, `barssince()` antiguo)
   - **SI**: `request.security()`, `ta.barssince()`, `array.new<float>()`

   **CHECKLIST OBLIGATORIO antes de finalizar:**
   - [ ] `//@version=6` en línea 1
   - [ ] `indicator(...)` declaration con `overlay` correcto (true para price-action, false para osciladores)
   - [ ] Todos los inputs tienen `title=` y `tooltip=` para UX
   - [ ] Plots usan `display.all` o `display.pane` apropiado
   - [ ] No hay `var` mal usados que causen NaN
   - [ ] Si tiene alertas: `alertcondition()` o `alert()` configurado
   - [ ] Comentarios explicando lógica no-trivial
   - [ ] Sin imports/librerías propietarias

4. **Guardar a library:**
   ```bash
   mkdir -p system/pine_library
   ```
   Guardar como `system/pine_library/<slug>.pine` con el código generado.

5. **Compilar en TradingView vía MCP:**
   ```
   pine_new(name="<Slug>")
   pine_set_source(<código>)
   pine_smart_compile()
   pine_get_errors()
   ```
   Si hay errores → corregir y re-intentar (max 3 ciclos).

6. **Reportar al usuario:**
   - Path del archivo guardado
   - Resumen del indicador (qué hace, qué inputs tiene, qué outputs visualiza)
   - Resultado de compilación (clean / warnings / errors corregidos)
   - Sugerencia de cómo agregarlo al chart en TradingView Desktop

## Output esperado

```markdown
🎨 PINE-GEN — vwap_bands_1sigma_2sigma

✅ Generado: system/pine_library/vwap_bands_1sigma_2sigma.pine (87 líneas)

## Resumen

**Indicador:** VWAP Bands con desviaciones 1σ y 2σ
**Tipo:** Overlay (sobre el price chart)
**Inputs:**
- Anchor (default: Session)
- Color upper bands (default: teal)
- Color lower bands (default: red)
- Show 1σ band (bool default true)
- Show 2σ band (bool default true)

**Outputs:**
- VWAP line (white, 2px)
- Upper 1σ + Upper 2σ bands
- Lower 1σ + Lower 2σ bands
- Background tint cuando precio fuera de 2σ
- Alerta: "Price crossed 2σ band" (frecuencia once_per_bar_close)

## Compilación

✅ Smart-compile: clean (0 errors, 0 warnings)
✅ Validated en TradingView Desktop

## Cómo usar

1. TradingView Desktop ya tiene el script abierto en el editor
2. Click "Add to chart" → indicador aparece en BTCUSDT.P
3. Configurar inputs en el icono de engranaje
4. Para alerta: right-click línea 2σ → "Add Alert"

🧠 Próximo paso opcional: `/backtest pine vwap_bands_1sigma_2sigma --tf 15m --bars 1000`
```

## Reglas

- **NO** generes Pine v5 ni v4 (Pine v6 obligatorio).
- **NO** llames APIs externas en el indicador (Pine no las soporta).
- **SI** el usuario describe un strategy completo (con buy/sell signals + backtest), preguntar primero si quiere `indicator()` (alertas) o `strategy()` (backtester). Diferencia importante:
  - `indicator()` → solo plots y alertas, no calcula PnL
  - `strategy()` → ejecuta órdenes virtuales, calcula PnL, drawdown, etc.
- Si el indicador requiere data multi-timeframe usar `request.security()`, NO `security()` (deprecated).
- Si el indicador requiere divergencias o pivots, usar `ta.pivothigh()` / `ta.pivotlow()`.
- Si la descripción es ambigua, asumir defaults razonables y notificarlos al usuario.

## Disclaimer

Pine Script generado por Claude debe ser **leído antes de usar en trading real**. AI puede:
- Interpretar mal una fórmula matemática
- Olvidar edge cases (divisiones por cero, NaN propagation)
- Sugerir alertas que disparan demasiado seguido (spam)

Tratar el output como un **draft** que necesita 1 revisión visual + 1 backtest antes de confiar en él.
