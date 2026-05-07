---
name: risk-parity
description: Risk Parity sizing multi-asset (FTMO/fotmarkets). Filtra A-grade penalizando
  assets sobre-volátiles.
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
<!-- generated from system/commands/risk-parity.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /risk-parity -->


Pasos que ejecuta Claude:

1. **Validar profile (multi-asset only):**
   ```bash
   PROFILE=$(python3 .claude/scripts/profile.py get)
   ```
   - Si profile == `retail` o `retail-bingx` → ABORTAR con: "Risk Parity requiere profile multi-asset (ftmo o fotmarkets)"
   - Si profile == `ftmo` → universo: BTC, ETH, EURUSD, GBPUSD, NAS100, SPX500
   - Si profile == `fotmarkets` → leer `phase_progress.md` para obtener `allowed_assets` de la fase actual

2. **Pull bars 1H de cada asset (en paralelo):**
   Para cada asset:
   ```
   mcp__tradingview__chart_set_symbol <TV_SYMBOL>
   mcp__tradingview__chart_set_timeframe 60
   mcp__tradingview__data_get_ohlcv summary=false limit=20
   ```
   Mapeo TV symbols:
   - BTC → BINANCE:BTCUSDT
   - ETH → BINANCE:ETHUSDT
   - EURUSD → OANDA:EURUSD
   - GBPUSD → OANDA:GBPUSD
   - NAS100 → OANDA:NAS100USD
   - SPX500 → OANDA:SPX500USD
   - XAUUSD → OANDA:XAUUSD

   Guardar cada uno a `/tmp/bars/<ASSET>.json`.

3. **Calcular vols realized + risk parity weights:**
   ```bash
   python3 .claude/scripts/risk_parity.py \
     --bars-dir /tmp/bars/ \
     --window 20 \
     --capital <CAPITAL> \
     --target-portfolio-vol 0.005
   ```

4. **Interpretar output:**
   - Para cada asset: weight % del portfolio + notional USD recomendado
   - Identificar **outliers**: assets cuyo weight RP es <50% del weight uniforme (1/N) → "asset volátil, riesgo concentrado"
   - Identificar **favorites**: assets cuyo weight RP es >150% del uniforme → "vol baja, OK para size más agresivo"

5. **Output recomendación:**
   ```
   Asset       Vol(20)   RP Weight   Notional      Verdict
   BTC         2.3%      8.6%        $860          ⚠️ vol alta — reducir size 50% si seleccionado
   EURUSD      0.4%      37%         $3,700        ✅ vol baja — candidato A-grade
   NAS100      1.5%      9.8%        $980          ⚠️ vol alta
   ...

   RANKING A-grade (vol-adjusted):
   1. EURUSD — vol 0.4%, weight 37%
   2. GBPUSD — vol 0.5%, weight 30%
   3. SPX500 — vol 1.2%, weight 12%
   4. NAS100 — vol 1.5%, weight 10%
   5. BTC    — vol 2.3%, weight 6.5%   [skip si setup débil]
   6. ETH    — vol 3.1%, weight 4.8%   [skip si setup débil]
   ```

## Integración con `morning-analyst-ftmo`

El agente puede invocar `/risk-parity` automáticamente después de identificar los setups candidatos en cada asset, y usar el ranking para priorizar la selección A-grade.

Regla recomendada: **NO operar el asset con weight <50% del uniforme a menos que el setup sea 4/4 filtros + ML score >70**.

## Limitaciones

- Asume independencia entre assets — no captura correlación (BTC-ETH ~0.85). Para ajuste real usar covariance matrix.
- Window 20 bars 1H = 20h ≈ 1 día — puede no capturar regime change.
- Risk parity NO es timing — sigue necesitando los filtros de entry.

$ARGUMENTS
