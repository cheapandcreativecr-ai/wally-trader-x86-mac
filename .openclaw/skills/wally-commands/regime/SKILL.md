---
name: regime
description: Detecta rápidamente el régimen del mercado (RANGE/TRENDING/VOLATILE)
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
<!-- generated from system/commands/regime.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /regime -->


Invoca el agente `regime-detector` para clasificar el mercado BTCUSDT.P.

Devuelve:
- RANGE / TRENDING UP / TRENDING DOWN / VOLATILE
- Evidencia con data 4H y 1H
- Estrategia recomendada (Mean Reversion / Donchian Breakout / NO OPERAR)
- Niveles macro relevantes

Tiempo estimado: < 1 minuto.

## Profile-aware logic

Comportamiento según profile activo (retail / ftmo / fotmarkets).

1. Lee profile: `PROFILE=$(python3 .claude/scripts/profile.py get)`

2. SI profile == "retail":
   - BTCUSDT.P 4H + 1H
   - Régimenes: RANGE / TRENDING UP / TRENDING DOWN / VOLATILE
   - Basado en ATR multiplier + distance from extremes
   - **ADX(14, 1H) obligatorio** vía `python3 .claude/scripts/adx_calc.py --file /tmp/bars1h.json --quick`:
     - ADX < 20 → RANGE_CHOP (Mean Reversion 15m primaria)
     - ADX 20-25 → TRANSITION (cautela, esperar señal clara)
     - ADX 25-30 → TREND_LEVE (Mean Reversion aún viable, pullback en dirección)
     - ADX 30-40 → TREND_FUERTE (Donchian Breakout secundaria)
     - ADX > 40 → TREND_EXTREMO (NO operar reversiones)
   - Dirección: +DI vs -DI

3. SI profile == "ftmo":
   - Aplica al asset preguntado (BTC/ETH/EURUSD/GBPUSD/NAS100/SPX500), no solo BTC
   - **ADX(14, 1H)** mismo protocolo que retail. Thresholds:
     - ADX < 20 → RANGE_CHOP (FTMO-Conservative válida si BB+RSI extremos)
     - ADX 20-30 → ZONA ÓPTIMA para FTMO-Conservative (pullback after pull)
     - ADX > 30 → TREND fuerte (operar solo en dirección, evitar contra-tendencia)
     - ADX > 40 → NO scalping, solo runner trend si ya en posición
   - Forex/Indices peso ADX > peso ATR-range

4. SI profile == "fotmarkets":
   - Forex/Indices requiere ADX principalmente (no BTC-style range detection)
   - Métricas:
     - ADX(14) en 15m:
       - ADX < 20 → RANGE (lateral, operable con strategy actual solo si hay soporte/resistencia tight)
       - ADX 20-30 → TREND leve (ideal para Fotmarkets-Micro pullback)
       - ADX > 30 → TREND fuerte (operar solo a favor, evitar reversiones)
       - ADX > 40 → TREND extremo (no operar scalping reversal)
     - +DI vs -DI: dirección del trend
   - Output:
     ```
     Asset: <X>
     ADX(15m): <val>
     Régimen: <RANGE|TREND_LEVE|TREND_FUERTE|TREND_EXTREMO>
     +DI: <val> | -DI: <val>
     Dirección: <LONG_BIAS|SHORT_BIAS|NEUTRAL>
     Recomendación Fotmarkets-Micro: <OPERAR|PAUSAR|SOLO_LONG|SOLO_SHORT>
     ```
