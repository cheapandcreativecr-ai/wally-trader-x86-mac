---
name: signal
description: Valida una señal externa de comunidad contra tu sistema — GO/NO-GO
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
<!-- generated from system/commands/signal.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /signal -->


Invoca el agente `signal-validator` para validar una señal externa antes de ejecutarla.

## Formatos aceptados

Ejemplos:
- `/signal Short XLM @ 0.1822`
- `/signal LONG ETH 2850 SL 2800 TP 2950`
- `/signal Sabueso: compra BTC 75000 stop 74800 target 76500`
- `/signal SHORT SOL 180.50` (sin SL/TP, los calcula)

## Qué hace el agente

1. **Parsea** la señal (símbolo, dirección, entry, SL, TP)
2. **Cambia chart** al símbolo de la señal
3. **Aplica tu sistema completo** — régimen, Mean Reversion, ICT, chartismo, Fibonacci, Elliott, indicadores
4. **Score de confluencia** — cuenta factores a favor y en contra (scale -10 a +10)
5. **Decisión clara:**
   - +7 a +10 → GO fuerte (size 1.5×)
   - +4 a +6 → GO moderado (size 1×)
   - +2 a +3 → GO tentativo (size 0.5×)
   - -1 a +1 → ESPERA
   - -2 a -10 → NO-GO
6. **Position sizing** con regla 2% de tu capital actual
7. **Niveles exactos** si decides ejecutar
8. **Dibuja la señal** en TV

## Protección

- Nunca aprueba trades con R:R < 1:1.5
- Nunca recomienda leverage > 10x
- Si el precio ya pasó el entry → marca como "perdiste trade"
- En altcoins pequeñas → advertencia de riesgo extra

## Señal a validar

$ARGUMENTS

## Auto-log para profile `bitunix`

Si `$WALLY_PROFILE` es `bitunix`, después de generar el reporte completo de validación, pipear el reporte al log automático.

El reporte debe estar en formato markdown estructurado con campos:
- `**Symbol:** <SYMBOL>`
- `**Side:** LONG|SHORT`
- `**Entry:** <num>`, `**SL:** <num>`, `**TP:** <num>`
- `**Leverage signal:** <num>x`
- `**Day-of-week:** <Mon|Tue|...>`
- `**4 filtros técnicos:** N/4`, `**Multi-Factor:** ±N`, `**ML:** N`
- `**Chainlink delta:** N%`
- `**Régimen:** RANGE|TRENDING|VOLATILE`
- `**4-Pilar Neptune SMC:** N/4`
- `**Saturday Protocol:** ...`
- `**Veredicto:** APPROVE_FULL|APPROVE_HALF|REJECT`
- `**Validation Score:** N/100`
- `**Decisión:** <texto>`

Pipear así:
```bash
echo "<reporte completo en markdown>" | WALLY_PROFILE=bitunix python3 .claude/scripts/bitunix_log.py append-signal --stdin
```

Comportamiento:
- Si stdout muestra `bitunix_log: appended ...` → log OK
- Si stderr muestra `WARNING: bitunix_log parse failed` → reportar al usuario `⚠️ Parse del log falló — revisa .claude/cache/bitunix_log_errors.log`. El report al usuario sigue siendo válido.
- Si profile no es bitunix → no hacer nada extra (el script será no-op).
