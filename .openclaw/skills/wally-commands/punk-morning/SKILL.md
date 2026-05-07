---
name: punk-morning
description: Preparación pre-sesión bitunix con scan exhaustivo + Neptune setup [solo
  bitunix]
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
<!-- generated from system/commands/punk-morning.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /punk-morning -->


Preparación pre-sesión específica para profile `bitunix` (copy-validated punkchainer's).

A diferencia de `/morning` (que dispatcha por profile), este comando es **bitunix-only** y NO genera entradas — prepara el terreno para recibir señales Discord:
- Macro events gate
- Scan exhaustivo de 10+ assets del watchlist punkchainer's
- Neptune indicators cargados en TV (Signals + Oscillator default)
- Helper `swap_neptune` documentado para validar señales con SMC/ICT
- Slots concurrentes (X/2 abiertas) y daily cap (X/7 ejecutadas)
- Reglas hot del día (DUREX trigger, Saturday Precision si aplica)

## Pasos que ejecuta Claude

1. **Profile guard (hard fail):**
   ```bash
   PROFILE=$(python3 .claude/scripts/profile.py get | awk '{print $1}')
   if [ "$PROFILE" != "bitunix" ]; then
     echo "❌ /punk-morning es exclusivo de profile bitunix. Profile activo: $PROFILE"
     echo "   Switch con: /profile bitunix"
     exit 1
   fi
   ```

2. **Despacha al agente `punk-morning-analyst`** con las 14 fases documentadas en
   su SKILL.md / definición de agente.

3. **Argumento opcional `$ARGUMENTS`:**
   - `quick` → versión liviana (solo macro + slots + Neptune setup, sin scan exhaustivo)
   - texto libre → contexto adicional (ej. "/punk-morning sin café" se propaga al agente)

## Output esperado

Dashboard markdown con:
- 🟢/🔴/⚪ macro flag (eventos próximas 6h)
- Capital actual / Slots disponibles (X/2) / Trades hoy (X/7)
- Top-3 assets más probables de señal HOY (basado en multifactor lite + correlación BTC + ATR%)
- Neptune setup confirmado en TV (Signals + Oscillator) + entity_ids
- DUREX trigger reminder
- Saturday Precision rules si fecha ∈ {Sat, Sun}
- Verdict: OPERAR / ESPERAR / NO OPERAR HOY
- Recordatorio final: "esperando señal Discord — al recibir, ejecutá `/signal SYMBOL SIDE entry sl=X tp=Y`"

## Reglas

- **NUNCA** abre trade — sólo prepara contexto
- **NUNCA** se ejecuta fuera de profile bitunix
- Si TV no está abierto, intenta `tv_launch` (igual que `/morning`)
- Si macro event <30 min → output incluye 🔴 MACRO ALERT y verdict NO OPERAR

Si hay argumentos, úsalos como contexto adicional al agente:

$ARGUMENTS
