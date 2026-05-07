---
name: chainlink
description: Cross-check de precio actual vs Chainlink Data Feeds (oráculo on-chain).
  Detecta discrepancias TV vs precio agregado real.
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
<!-- generated from system/commands/chainlink.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /chainlink -->

<!-- args: [PAIR] default BTC, soporta BTC ETH LINK EUR GBP XAU -->

Pasos que ejecuta Claude:

1. **Determinar par a checkear:**
   - Si `$ARGUMENTS` está vacío → default `BTC`
   - Si `$ARGUMENTS` es un par válido (`BTC`, `ETH`, `LINK`, `EUR`, `GBP`, `XAU`) → usar ese
   - Si es otro símbolo → mapear: `BTCUSDT.P` → `BTC`, `ETHUSDT.P` → `ETH`, `EURUSD` → `EUR`, etc. Si no mapea, retornar error.

2. **Obtener precio TradingView del símbolo activo:**
   ```bash
   # Vía MCP — usar mcp__tradingview__quote_get para obtener last price
   ```
   Si no hay TV abierto / símbolo no coincide, omitir compare y solo mostrar precio Chainlink.

3. **Llamar al helper:**
   ```bash
   python3 .claude/scripts/chainlink_price.py $PAIR --compare $TV_PRICE
   ```

4. **Interpretar veredicto:**
   - **OK** (delta <0.3%) → "Precio TV confiable. Procede con análisis."
   - **WARN** (delta 0.3-1%) → "Posible lag/exchange-specific. Validar setup pero NO bloquear."
   - **ALERT** (delta >1%) → "BLOCK trading. Probable feed stale o manipulación. Verifica TV symbol/exchange."

5. **Casos de uso típicos:**
   - **Pre-entry validation:** después de los 4 filtros, antes de ejecutar.
   - **Post-SL forensics:** si SL pegó en wick, comparar Chainlink en ese minuto vs TV.
   - **Cross-exchange divergence:** Binance vs spot global — útil para detectar premium/discount.
   - **Multi-asset (FTMO/fotmarkets):** validar EURUSD, GBPUSD, XAUUSD contra Chainlink antes de trade.

6. **Output esperado:**
   ```
   Chainlink BTC/USD : $75,479.71
   TradingView BTC   : $75,500.00
   Delta             : 0.027%   [OK]
   → Sin discrepancia significativa, precio TV confiable.
   ```

## Limitaciones a recordar al usuario

- **Solo pares con feed Ethereum mainnet** soportados (BTC, ETH, LINK, EUR, GBP, XAU).
- Pares no soportados: `BTCUSDT.P` exchange-specific (Chainlink agrega global), `NAS100`, `SPX500`.
- **Latencia Chainlink:** updates cada heartbeat (~3-30 min según feed) o por desviación. NO es tick-by-tick.
- **Cache 30s** para evitar hammear RPCs públicos.
- Si todos los RPCs fallan → cache stale o exit 1. Comunicar al usuario.

$ARGUMENTS
