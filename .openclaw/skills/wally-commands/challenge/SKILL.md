---
name: challenge
description: 'Wally Trader command: /challenge'
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
<!-- generated from system/commands/challenge.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /challenge -->

Dashboard de progreso del challenge FTMO.

Uso:
- `/challenge` — muestra estado completo del challenge

Pasos que ejecuta Claude:

1. Lee profile activo. Si != "ftmo":
   - Mensaje: "/challenge solo aplica al profile FTMO. Profile activo: <X>."
   - NO ejecutar

2. Lee `.claude/profiles/ftmo/config.md` y `.claude/profiles/ftmo/memory/challenge_progress.md`

3. Invoca: `python3 .claude/scripts/guardian.py --profile ftmo --action status`

4. Formatea el output:

```
╔══════════════════════════════════════════════╗
║  FTMO CHALLENGE DASHBOARD                     ║
║  Tipo: 1-Step $10,000                         ║
║  Status: <ACTIVE | PREPARING | BREACHED>       ║
╠══════════════════════════════════════════════╣
║  PROFIT TARGET 10% ($1,000)                   ║
║  Acumulado: $X ($P%)                          ║
║  Faltan:    $Y                                ║
║                                               ║
║  EQUITY                                       ║
║  Actual: $X (YY% desde inicio)                ║
║  Peak:   $X                                   ║
║                                               ║
║  REGLAS                                       ║
║  □ Daily 3%:     Used $X (Y% / 3% hoy)        ║
║  □ Trailing 10%: Used $X (Y% / 10% from peak) ║
║  □ Best Day 50%: Ratio Y% (cap 50%)           ║
║  □ Max trades/día: N/2 usados hoy             ║
║                                               ║
║  MÉTRICAS ROLLING                             ║
║  Días activos: N                              ║
║  WR: Y%                                       ║
║  Avg R: Y                                     ║
║  Profit factor: Y                             ║
║                                               ║
║  OVERRIDES GUARDIAN: N (review needed si >0)  ║
╚══════════════════════════════════════════════╝
```

5. Alertas si aplica:
   - Si profit_pct >= 10.0 → "🎯 CHALLENGE PASSED — Contacta FTMO para verificación"
   - Si cualquier regla BREACHED → "🚫 CHALLENGE BREACHED — <regla>. Cuenta nueva requerida."
   - Si overrides > 0 → "📋 Revisa overrides.log al /journal"

6. **AGREGADO DESDE NOTION FTMO DB (si Notion MCP activo):**
   - Lee `.claude/.env` para `NOTION_FTMO_DB_ID`. Verifica acceso a tools `mcp__notion_*`
   - Si disponible:
     - Query `mcp__notion__query_database` con filter por fecha >= fecha-inicio-challenge
     - Calcula agregados independientes:
       - Total trades (count): N
       - WR (rows con Result IN [TP1, TP2]): X%
       - Sum PnL $ (columna): $Y
       - Best day (groupby Date, max sum PnL $): $Z
       - Avg R multiple: W
     - Compara con métricas del guardian (equity_curve):
       - Si divergen >5% → warning: "⚠️ Notion vs local divergen. Corre /sync para reconciliar."
       - Si match → Notion sirve como backup visual, guardian sigue siendo source of truth
     - Agrega sección al dashboard:
       ```
       NOTION AGGREGATE (últimos N días challenge)
         Trades totales: N
         WR: X%
         PnL acumulado: $Y
         Best day: $Z
         Divergencia vs local: ✓ match / ⚠️ <delta>
       ```
   - Si query falla: silencioso, solo agregados locales
