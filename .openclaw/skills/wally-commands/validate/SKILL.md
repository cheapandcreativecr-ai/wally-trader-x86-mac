---
name: validate
description: Valida un setup de entrada ANTES de ejecutar el trade
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
<!-- generated from system/commands/validate.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /validate -->


Valida un setup de entrada ANTES de ejecutar el trade.

Pasos que ejecuta Claude:

1. Lee profile: `PROFILE=$(python3 .claude/scripts/profile.py get)`

2. SI profile == "retail":
   - Despacha agente `trade-validator`
   - Verifica los 4 filtros técnicos del config retail (Donchian + RSI + BB + close color)
   - Además 5° filtro ML opcional (vía /ml si el setup es 4/4)
   - Veredicto: GO / NO-GO tradicional

3. SI profile == "ftmo":
   - Despacha agente `trade-validator` con instrucción "usar filtros de FTMO-Conservative"
   - Verifica los 7 filtros (ver `profiles/ftmo/strategy.md` sección 5.4)
   - Si todos los 7 OK:
     - Invoca guardian:
       ```
       python3 .claude/scripts/guardian.py --profile ftmo --action check-entry \
         --asset <ASSET> --entry <ENTRY> --sl <SL> --loss-if-sl <USD_LOSS>
       ```
     - Procesa veredicto:
       - OK → "GO absoluto"
       - OK_WITH_WARN → muestra warnings en rojo, pide confirmación explícita del usuario
       - BLOCK_SIZE → "size reducir a X% del propuesto, luego confirmar"
       - BLOCK_HARD → "NO-GO. Razón: <reason>. Opción override: escribir literalmente 'OVERRIDE GUARDIAN'"

3.5. SI profile == "fotmarkets":
   - Invoca Lite Guardian primero:
     ```
     GUARD=$(python3 .claude/scripts/fotmarkets_guard.py check)
     ```
     Si `GUARD` empieza con `BLOCK`:
       - Muestra razón al usuario
       - Pregunta si quiere proceder con `OVERRIDE FOTMARKETS` (regla R10 de rules.md)
       - Si NO → abortar validación con NO-GO
       - Si OVERRIDE → continuar pero registrar en `memory/overrides.log`

   - Despacha agente `trade-validator` con contexto:
     - "Usar filtros de Fotmarkets-Micro (ver .claude/profiles/fotmarkets/strategy.md sección 3)"
     - 4 filtros obligatorios LONG o SHORT según dirección propuesta
   
   - Verifica que asset esté en whitelist de la fase actual:
     - `PHASE=$(python3 .claude/scripts/fotmarkets_phase.py)`
     - Cargar `phase_N.allowed_assets` de config.md
     - Si asset NO en whitelist → NO-GO con mensaje "Asset <X> desbloqueado en Fase Y+"
   
   - Si 4/4 filtros + asset whitelist OK:
     - Calcula sizing invocando `/risk` con datos del setup
     - Valida hard stops (ATR, spread, noticias) via strategy.md sección 7
     - Si algún hard stop activo → NO-GO con razón
     - Si todo OK → "GO" con mostrar:
       ```
       Asset:      <X>
       Fase:       <N>
       Entry:      <P>
       SL:         <P> (dist <D> pips / X%)
       TP:         <P> (R=2.0)
       Lots:       <lots>
       Risk USD:   $<X>
       Risk %:     <phase_risk_pct>% del capital actual ($<CAP>)
       Guardian:   PASS
       Filtros:    4/4 ✓
       ```
   
   - Si usuario escribe "OVERRIDE FOTMARKETS":
     - Append a `.claude/profiles/fotmarkets/memory/overrides.log`:
       `<timestamp>|fotmarkets|<rule_violated>|<capital>|<trade_json>|<user_reason>`
     - Procede con "GO" pero con warning

4. Formato de output estándar:

```
TÉCNICO: N/N filtros ✓
GUARDIAN: <VEREDICTO> — <razón>

Setup:
  Asset:  <X>
  Entry:  <P>
  SL:     <P> (dist <D%>)
  TP1:    <P> (R:R 1.5)
  TP2:    <P> (R:R 3.0)
  Size:   <lots/BTC> (risk $<X>)

Acción: <GO | CONFIRM | NO-GO>
```

5. Si usuario escribe "OVERRIDE GUARDIAN":
   - Append a `.claude/profiles/ftmo/memory/overrides.log`:
     `<timestamp>|ftmo|<rule_violated>|<equity>|<trade_json>|<user_reason>`
   - Procede con "GO" pero con warning grande

6. **[FTMO ONLY] Si veredicto final GO (7/7 filtros + guardian OK/OK_WITH_WARN):**
   
   Pregunta al usuario:
   ```
   ¿Ejecutar orden ahora?
   
   Responde:
   - YES → encolar al EA (o manual si offline)
   - AJUSTAR <size|sl|tp> <valor> → modificar param y re-validar
   - NO → solo guardar setup en memoria, no ejecutar
   ```
   
   a. Si responde **YES**:
      - Invoca flujo de `/order` con los parámetros del setup validado (7/7 + guardian OK)
      - Pasa directamente a la confirmación YES de `/order` (usuario ya aprobó en /validate)
      - Usa mismo `guardian_verdict` y `filters_passed=7`
      - Output: muestra tabla ASCII de orden encolada (mismo formato que `/order`)
   
   b. Si responde **AJUSTAR X Y**:
      - Actualiza param (size, sl, o tp)
      - Re-valida guardian con nuevo param
      - Re-pide confirmación (vuelve a paso 6)
   
   c. Si responde **NO** o nada:
      - Display: "Setup guardado en memoria. Usa `/order` después para ejecutar."
      - NO escribe a pending_orders.json ni mt5_commands.json

Contexto adicional (opcional):
$ARGUMENTS
