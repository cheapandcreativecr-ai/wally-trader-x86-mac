---
name: dashboard
description: Dashboard multi-profile — resumen rápido de TODOS los profiles activos
  en una vista
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
<!-- generated from system/commands/dashboard.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /dashboard -->


# /dashboard

Vista cross-profile rápida — equity de cada profile, exposiciones activas, daily PnL, último trade. Para ver el estado general del sistema antes de cualquier decisión.

## Steps

1. Lee profile activo: `PROFILE=$(python3 .claude/scripts/profile.py get)` (solo informativo).

2. Itera sobre TODOS los profiles (`retail`, `retail-bingx`, `ftmo`, `fotmarkets`, `fundingpips`, `bitunix`, `quantfury`).

3. Para cada profile, recopila:
   - **Capital actual** (config.md o equity_curve last entry)
   - **Daily PnL** (si hay actividad hoy)
   - **Trades hoy** (count en trading_log.md)
   - **Pending orders activas** (pending_orders.json status != terminal)
   - **Exposición direccional** (last open trade, open|closed)

4. Renderiza tabla resumen:

```
=== WALLY DASHBOARD — 2026-04-30 14:30 CR ===
                                                                              
Profile        Capital        Daily PnL    Trades  Pending  Exposure         
─────────────  ─────────────  ───────────  ──────  ───────  ───────────────  
► retail       $18.09 ≈₡8.2K  -            0/3     0        flat             
  retail-bingx $0.93 ≈₡423    -            0/3     0        flat             
  ftmo         $10,000        +0.0%        0/3     0        flat             
  fotmarkets   $33.84         -            0/1     0        flat             
  fundingpips  $10,000        -            0/2     0        flat             
  bitunix      $50.00         -            0/3     0        flat             
  quantfury    0.01 BTC≈$830  +0.0% (BTC)  0/3     0        flat             

Cross-profile collisions: 🟢 NONE (0 same-asset+side overlaps)

Last activity: fotmarkets EURUSD long 2026-04-27 12:34 → result TP1
```

5. Si hay collisions cross-profile → mostrar prominently:
   ```
   ⚠️  CROSS-PROFILE COLLISION:
       retail BTC long + bitunix BTCUSDT.P long → DOUBLE EXPOSURE
       Resolve: close one before opening another
   ```

6. Marker `►` indica profile activo.

## Notas

- Si profile no tiene memoria poblada → muestra "no data" en columna apropiada
- Daily PnL requiere `equity_curve.csv` o trading_log.md actualizado HOY
- Pending count usa `cross_profile_guard.py status` para data live

## Implementación (referencia)

```bash
python3 .claude/scripts/cross_profile_guard.py status   # JSON exposures
python3 .claude/scripts/profile.py get                   # active profile

# Helper futuro: dashboard.py que orquesta todo
python3 .claude/scripts/dashboard.py
```

Si `dashboard.py` no existe aún, render manual con los datos disponibles.
