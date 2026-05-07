---
name: last-trade
description: Análisis del último trade ejecutado del profile activo (entry, exit,
  lecciones)
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
<!-- generated from system/commands/last-trade.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /last-trade -->


# /last-trade

Recupera el último trade del profile activo y lo analiza: entry context, exit, PnL, lección aprendida. Útil después de cerrar un trade para journaling rápido o para revisar mientras consideras un nuevo trade similar.

## Steps

1. Lee profile activo: `PROFILE=$(python3 .claude/scripts/profile.py get)`

2. Localiza trading_log.md: `.claude/profiles/$PROFILE/memory/trading_log.md`

3. Parse el último trade (última fila no-vacía de la tabla markdown).

4. Recopila contexto adicional:
   - Régimen al momento del entry (consultar `/regime` si data ese día está disponible)
   - Multi-Factor score si fue trackeado
   - ML score si fue trackeado
   - Sentiment score del día
   - Resultado vs filtros pre-entry

5. Renderiza análisis:

```
=== LAST TRADE — 2026-04-27 12:34 CR ===
Profile:       fotmarkets
Asset / Side:  EURUSD long (market)
Entry:         1.0850
SL:            1.0820 (-30 pips)
TP1:           1.0880 (+30 pips, R:R 1:1)
TP2:           1.0910 (+60 pips, R:R 1:2)

Pre-entry context:
  Régimen:       RANGE (London open)
  Multi-Factor:  +52 (LONG bias)
  ML score:      57 (LONG)
  Sentiment:     65 (greed mild)
  4 filtros:     4/4 ✓

Outcome:
  Exit:          1.0882 at 13:15 CR
  Reason:        TP1 hit
  PnL:           +$3.50 (+11.7% account at 10% risk)
  Time held:     41 min
  Result:        WIN

Lección: setup A-grade en RANGE confirmado por todos filters. Replicar.
Anota en trading_log.md si no está ya:
  "TP1 hit limpio. Validation worked. Filtro Adjusted CHoCH evitó early entry."
```

6. Si hay un signal pattern para reproducir → sugerir siguiente acción:
   - Si fue LOSS: "Considera review en `/journal` antes de próximo trade"
   - Si fue WIN: "Setup replicable detectado. Buscar similar mañana."

## Notas

- Si profile no tiene trades → "No trades en {profile}/trading_log.md"
- Si últimas 5 entries son del mismo día → puede mostrar resumen de la sesión completa en lugar de un solo trade
- Para profile bitunix → además consulta `signals_received.md` para incluir validation pipeline data

## Implementación

```bash
# Manual parse del trading_log.md
tail -10 .claude/profiles/$PROFILE/memory/trading_log.md | grep "^|" | tail -1
```

(Helper futuro: `python3 .claude/scripts/last_trade_analyzer.py` para análisis automatizado.)
