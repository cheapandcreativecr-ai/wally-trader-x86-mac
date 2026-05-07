---
name: levels
description: Muestra niveles técnicos actuales (Donchian, BB, RSI, ATR) del asset
  activo del profile
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
<!-- generated from system/commands/levels.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /levels -->


Niveles técnicos actuales del asset activo del profile.

Pasos que ejecuta Claude:

1. Lee profile: `PROFILE=$(python3 .claude/scripts/profile.py get)`

2. Determina símbolo a analizar:
   - retail → `BINGX:BTCUSDT.P` (único asset)
   - ftmo → pregunta al usuario cuál asset de los 6 del universo quiere (o usa el último analizado en morning)
   - fotmarkets → pregunta al usuario cuál asset de los allowed_assets de la fase actual

3. Determina timeframe primario del profile:
   - retail → 15m
   - ftmo → 15m
   - fotmarkets → 5m

4. Cambia TF al del profile y pull últimas 50 velas (excluir la forming)

5. Calcula:
   - **Donchian(20)** High y Low (en retail usa 15)
   - **Bollinger Bands(20, 2)** upper, mid, lower
   - **RSI(14)** actual
   - **ATR(14)** actual
   - **EMA 50** (si hay 50+ barras disponibles)
   - **EMA 200** (si hay 200+ barras)

6. Identifica:
   - Distancia del precio actual a cada nivel (%)
   - Cuál está más cerca (soporte o resistencia)
   - Si precio está dentro de zona de entrada (±0.15% de Donchian H/L para fotmarkets, ±0.1% para retail/ftmo)

7. Entrega:
   - Tabla con todos los niveles
   - Precio actual vs nivel más cercano
   - Recomendación rápida: ¿esperar, vigilar, o ya está en zona?

Formato compacto, máximo 20 líneas de output.

Si argumentos adicionales ($ARGUMENTS) → usar como símbolo override (ej: `/levels EURUSD`).
