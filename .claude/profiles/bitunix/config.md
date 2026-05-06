# Profile: BITUNIX (copy trading punkchainer's community)

**Capital:** $200.00 USD inicial (recalibrado 2026-05-04 — capital real punkchainer's copy-validated)
**Plataforma:** [Bitunix](https://bitunix.com) — exchange crypto perpetual futures
**Referral code:** `punkchainer` (descuento en fees, igual que la comunidad)
**Modelo:** **NO ES ANÁLISIS PROPIO.** Es validación + copia de señales de la comunidad punkchainer's.
**Objetivo PnL diario:** $20-100 (5+ wins / 7 attempts con WR ~70% y R:R 2:1 → 5:1)

## Filosofía operativa (actualizada 2026-05-04)

> El edge aquí NO es generar señales. Es **filtrar las malas**.

### 🎯 Filosofía CORE: ROTACIÓN ALTA — 1 trade/hora

**Target:** 1 trade ejecutado cada ~1 hora durante ventana operativa (CR 06:00-23:00 = ~17h × 1/h posible). Capturar lo que el mercado da en ventanas cortas, NO esperar movimientos largos.

**Implicaciones operativas:**

1. **TPs adaptativos al contexto + tiempo** (ver `system/agents/punk-hunt-analyst.md` Phase 6 + helper `.claude/scripts/context_multiplier.py`):
   - TP1 debe ser alcanzable en <60 min con probabilidad alta
   - TP2 en <2h, TP3 runner extendido
   - Si setup requiere >2h para TP1 → SCORE penalty o REJECT

2. **Time-out forzado a 90 min** (ver `rules.md`):
   - Si trade lleva >90 min sin TP1 hit → cerrar manual o ajustar TPs vía `/punk-watch`
   - Excepción: `/punk-watch` recomienda explícitamente "AGUANTAR" por catalyst próximo

3. **Salida disciplinada > esperar el "trade del día"**:
   - +$0.50 capturado en 30 min × 8 trades/día = $4 (2% capital)
   - $5 esperando un TP3 que no llega = mucho riesgo y oportunidad perdida

4. **`/punk-watch` cada 30 min mientras hay trade activo**:
   - Recalcula contexto, sugiere ajuste TPs/SL si cambió >15%
   - Forecast catalyst próximas 4-12h
   - Decide CERRAR/AGUANTAR/AJUSTAR basado en data

La comunidad punkchainer's en Discord publica señales de trading (BTC, ETH, MSTRUSDT, otros perpetual). El bot `PunkAlgo` postea dirección/leverage/entry. Tu sistema valida CADA señal con tus filtros propios antes de copiar:

- ¿4 filtros técnicos alineados? (`/signal` agent)
- ¿Multi-Factor score >+50 (long) o <-50 (short)?
- ¿ML XGBoost score >55?
- ¿Chainlink price valida (no wick fake)?
- ¿Régimen del asset compatible con dirección?

**Si pasa todo → COPIAR.**
**Si falla cualquiera → SKIP** (la comunidad puede usar lógica distinta a la tuya).

Este profile es perfecto para:
1. **Validar el edge de la comunidad** (¿cuántas de sus señales pasan tus filtros?)
2. **Aprender por contraste** (¿qué señales tomaron ellos que tú rechazaste y resultaron WIN?)
3. **Diversificar capital** sin replicar setups de retail/FTMO

## Universo de assets

**Dinámico** — depende de lo que la comunidad señale en cualquier momento.

**Watchlist exhaustivo (32 assets)** que `/punk-morning` y `/punk-hunt` pre-scanean cada sesión:

**Tradeables en Bitunix (chart Bitunix:.P) — 24 assets:**

| # | Symbol | TV Symbol | Categoría |
|---|---|---|---|
| 1 | BTCUSDT.P | `Bitunix:BTCUSDT.P` | Major |
| 2 | ETHUSDT.P | `Bitunix:ETHUSDT.P` | Major |
| 3 | SOLUSDT.P | `Bitunix:SOLUSDT.P` | L1 |
| 4 | MSTRUSDT.P | `Bitunix:MSTRUSDT.P` | BTC-proxy |
| 5 | AVAXUSDT.P | `Bitunix:AVAXUSDT.P` | L1 |
| 6 | INJUSDT.P | `Bitunix:INJUSDT.P` | L1 |
| 7 | DOGEUSDT.P | `Bitunix:DOGEUSDT.P` | Memecap |
| 8 | WIFUSDT.P | `Bitunix:WIFUSDT.P` | Memecap |
| 9 | FARTCOINUSDT.P | `Bitunix:FARTCOINUSDT.P` | Memecap |
| 10 | XLMUSDT.P | `Bitunix:XLMUSDT.P` | L1 payments |
| 11 | TONUSDT.P | `Bitunix:TONUSDT.P` | L1 (Telegram) |
| 12 | ADAUSDT.P | `Bitunix:ADAUSDT.P` | L1 (Cardano) |
| 13 | LINKUSDT.P | `Bitunix:LINKUSDT.P` | Oracle infra |
| 14 | SUIUSDT.P | `Bitunix:SUIUSDT.P` | L1 (Sui) |
| 15 | TRXUSDT.P | `Bitunix:TRXUSDT.P` | L1 (Tron) |
| 16 | RUNEUSDT.P | `Bitunix:RUNEUSDT.P` | DeFi (THORChain) |
| 17 | ENJUSDT.P | `Bitunix:ENJUSDT.P` | Gaming/NFT |
| 18 | CHZUSDT.P | `Bitunix:CHZUSDT.P` | Sport tokens |
| 19 | AXSUSDT.P | `Bitunix:AXSUSDT.P` | Gaming (Axie) |
| 20 | SEIUSDT.P | `Bitunix:SEIUSDT.P` | L1 (Sei) |
| 21 | POLUSDT.P | `Bitunix:POLUSDT.P` | L2 (Polygon, ex-MATIC) |
| 22 | HBARUSDT.P | `Bitunix:HBARUSDT.P` | L1 (Hedera) |
| 23 | TIAUSDT.P | `Bitunix:TIAUSDT.P` | DA layer (Celestia) |
| 24 | ROSEUSDT.P | `Bitunix:ROSEUSDT.P` | Privacy L1 (Oasis) |

**NO tradeables en Bitunix (sólo vigilancia/contexto vía chart fallback) — 8 assets:**

| # | Symbol | TV Symbol Fallback | Categoría |
|---|---|---|---|
| 25 | PEPEUSDT.P | `OKX:PEPEUSDT.P` | Memecap |
| 26 | PIPPINUSDT.P | `Binance:PIPPINUSDT.P` | Memecap AI |
| 27 | BCHUSDT (spot) | `Binance:BCHUSDT` | Major BTC fork (sin .P) |
| 28 | MONUSDT.P | `Bybit:MONUSDT.P` | L1 (Monad) |
| 29 | XAUTUSDT (spot) | `Bitunix:XAUTUSDT` | Tether Gold (sin .P) |
| 30 | STRKUSDT.P | `Bybit:STRKUSDT.P` | L2 ZK (Starknet) |
| 31 | XMRUSDT.P | `Bybit:XMRUSDT.P` | Privacy (Monero) |
| 32 | BANANAS31USDT.P | `Binance:BANANAS31USDT.P` | Memecap |

**TIER 0 MUGRE (meme/low-cap, score≥80 obligatorio) — 9 assets operables:**

Subset opt-in para `/punk-hunt --tier-0`. Tokens del canal `mugre-signals` de la comunidad punkchainer's con perfil de **volatilidad extrema + liquidez frágil**. Reglas estrictas (ver `rules.md` #11): score ≥80, leverage cap 3x, margin cap 15% capital ($30), risk 1% ($2), DUREX a 1R.

| # | Symbol | TV Symbol | Vol 24h | Categoría | Listed (2026-05-05) |
|---|---|---|---|---|---|
| 33 | BIOUSDT.P | `Bitunix:BIOUSDT.P` | $5.86M | Narrative AI/Bio | ✅ HEALTHY |
| 34 | PENDLEUSDT.P | `Bitunix:PENDLEUSDT.P` | $5.03M | DeFi yields | ✅ HEALTHY |
| 35 | RAVEUSDT.P | `Bitunix:RAVEUSDT.P` | $12.79M | Memecap | ✅ HEALTHY |
| 36 | BSBUSDT.P | `Bitunix:BSBUSDT.P` | $22.38M | Memecap | ✅ HEALTHY |
| 37 | BASEDUSDT.P | `Bitunix:BASEDUSDT.P` | $2.16M | Memecap (Base) | ✅ HEALTHY |
| 38 | OPGUSDT.P | `Bitunix:OPGUSDT.P` | $0.58M | Memecap | ⚠️ THIN |
| 39 | BROCCOLIUSDT.P | `Bitunix:BROCCOLIUSDT.P` | $0.49M | Memecap | ⚠️ THIN |
| 40 | BANANAUSDT.P | `Bitunix:BANANAUSDT.P` | $0.49M | Memecap | ⚠️ THIN |
| 41 | POWRUSDT.P | `Bitunix:POWRUSDT.P` | $0.10M | Energy/RWA | ⚠️ THIN |

**Excluidos del watchlist (listed pero vol 24h = 0 → no operables):** DASH, AI, B3.

**Re-validar listings:** `python3 .claude/scripts/bitunix_pairs_check.py --tier 0` (cualquier momento, hits API pública sin auth).

**⚠️ Nota de performance:** scanear los 32 assets cada `/punk-hunt` toma ~3-5 min de MCP calls. Si querés invocaciones más rápidas, usá `/punk-hunt --asset SYMBOL` para forzar scan único, `/punk-hunt quick` para sólo los 5 más líquidos (BTC/ETH/SOL/DOGE/XLM), o `/punk-hunt --tier-0` para escanear solo el subset MUGRE (9 assets, ~1 min).

**Reglas importantes:**
- ⚠️ **Solo perpetuals tradeables** — los assets en la 2da tabla aparecen en scan pero el agente NUNCA los recomendará como entry tradeable en Bitunix (no podés ejecutar). Sirven para contexto/correlación.
- Si la comunidad señala asset NO en watchlist, `/signal` lo valida igual.
- Si Bitunix delistea o agrega assets, actualizar esta tabla manualmente.
- **TIER 0 MUGRE:** opt-in solamente. `/punk-hunt` standard NO escanea estos assets — solo `/punk-hunt --tier-0` los considera. Re-chequear listings/volumen mensualmente con `bitunix_pairs_check.py`.

## Reglas duras (ver `rules.md`)

| Regla | Valor | Tipo |
|---|---|---|
| Risk per signal | 2% capital ($4 sobre $200) | hard cap |
| **Max margin per trade** | **30-35% del capital** ($60-70 max) | hard cap (NO 50%+) |
| Max copied signals / día | **10** (rotación 1/h × ventana 10-17h) | BLOCK |
| Max concurrent open positions | **2** simultáneas | BLOCK nuevas |
| **Time-out por trade** | **90 min sin TP hit → cerrar manual** | regla anti-overstay |
| Min validation score | 60% (4 confluencias Elite Crypto) | gate |
| Max leverage | **20x** — sigue al leverage de la señal (excepción del cap 10x global). >20x = WARN, no override automático | profile-specific |
| Daily loss BLOCK | -6% capital ($12 sobre $200, ~3 SLs) | STOP día |
| Max DD del capital | -30% ($60 sobre $200) | STOP profile + review |
| Auto-blacklist asset | Después de 2 SLs consecutivos en mismo asset | filter |
| Ventana operativa | CR 06:00-23:00 (~17h) — mejor London/NY overlap | INFO |
| **TP gate** | TP1 debe ser alcanzable en <60 min con context actual | filter |

## Setup TradingView (indicadores Neptune comunidad)

La comunidad punkchainer's / Elite Crypto usa **7 indicadores Neptune** (Bangchan10, requieren invitación). Lista verificada con screenshot del usuario 2026-05-04:
1. `Neptune® - Money Flow Profile™` (29 boosts)
2. `Neptune® - Oscillator™` (72 boosts)
3. `Neptune® - Signals™` (50 boosts) — versión 2.0 integra oscilador interno
4. `Neptune® - Smart Money Concepts™` (74 boosts) — **incluye ICT** (SMC = ICT, mismo indicador)
5. `Pivots and Phases™` (19 boosts)
6. `Pivots and Phases™` (17 boosts) — versión alternativa
7. `SMC Oscillator™` (27 boosts)

**Configuraciones exactas:** ver skill `@neptune-community-config` (configs validadas para 15M-4H + nuevo Signals 2.0).

**Placeholders/webhooks:** ver skill `@neptune-alert-placeholders` (templates JSON listos para 3Commas/Cornix/webhooks).

**Videos referencia oficial:** 4 videos de Ponk (Elite Crypto) documentados en `@neptune-community-config` sección "Referencias". Cualquier ambigüedad de la metodología se resuelve con esos videos.

**Reglas críticas (Neptune Signals 2.0):**
- **Range Filter ON** (NUNCA deshabilitar — detecta lateral)
- **Reversal Bands ON** (herramienta favorita Ponk — "el precio siempre busca la banda")
- **Smooth Trail ON** (S/R dinámica — combo poderoso con Reversal Bands)
- **2 tipos señales:** triángulos (largos) + +/- (cortos), ambos con alertas separadas
- **X Signals ON** (reversal/take profit)
- Plan TV **Premium pagado** (confirmado 2026-05-04) = max **5 indicadores** → combo recomendado:
  1. `Neptune® - Signals™` (Range Filter, Reversal Bands, Smooth Trail, Trade Builder)
  2. `Neptune® - Smart Money Concepts™` (Áreas de Interés, FVG, OB, ICT)
  3. `Neptune® - Oscillator™` (Hyper Wave, Money Flow direction)
  4. `Pivots and Phases™` (fases del MIT + pivots azules)
  5. `Neptune® - Money Flow Profile™` (POC/VAH/VAL volume institucional)

**Setup específico bitunix:** `memory/neptune_setup.md` documenta el workflow de validación visual + cuantitativa para cada señal.

**Indicator swap dinámico (TV Basic constraint):** `/punk-morning` deja preparado un helper para que `/signal` pueda swappear el slot de Signals temporalmente para validar con Money Flow Profile o Pivots and Phases, manteniendo siempre el slot de SMC cargado. Nombres EXACTOS para `chart_manage_indicator`:
- `Neptune® - Signals™` (recomendado siempre cargado)
- `Neptune® - Smart Money Concepts™` (recomendado siempre cargado, **incluye ICT**)
- `Neptune® - Oscillator™` (alternativa al Signals 2.0 si querés oscilador en pane separado)
- `Neptune® - Money Flow Profile™` (swap temporal para volume profile)
- `Pivots and Phases™` (swap temporal para fases del mercado)
- `SMC Oscillator™` (alternativa SMC en formato oscilador)

⚠️ **NO existe `Neptune® - ICT Concepts™` como indicador separado** — está integrado en `Neptune® - Smart Money Concepts™`.

## Cómo funciona el flow

```
[Discord punkchainer's]
   ↓ señal nueva: "MSTRUSDT Short 20x entry 166.57"
   
[Tú lees y validas con Neptune en TU chart]
   1. Aplica config Neptune (ver skill neptune-community-config)
   2. Verifica visualmente: ¿flecha Signals? ¿confluencias Oscillator? ¿OB/FVG SMC?
   
[Si visual confirma → cuantitativo]
/signal MSTRUSDT short 166.57 sl=170 tp=160 leverage=20
   ↓
[Sistema valida con 4 capas]
   - 4 filtros técnicos
   - Multi-Factor score
   - ML XGBoost score
   - Chainlink cross-check
   ↓
[Veredicto]
   GO confidence>=60 → recomienda EJECUTAR (sigue leverage de señal hasta 20x)
   NO-GO confidence<60 → SKIP, anota razón en memory/signals_received.md
   
[Tú ejecutas manual en Bitunix]
   - Login Bitunix
   - Open MSTRUSDT-PERP, side SHORT
   - Size: 2% del capital con el leverage que diga la señal (max 20x)
   - SL en 170, TPs escalonados
   
[Tracking automático]
   /equity bitunix <new>  → actualiza equity_curve
   /journal              → log + outperformance metrics
```

## Reglas cross-profile

1. **NO copiar señal Bitunix de BTC si tienes posición BTC en retail/ftmo/quantfury.** Doble exposición = riesgo correlacionado.
2. **Leverage en Bitunix sigue al de la señal hasta 20x cap**. Excepción documentada del cap 10x global del proyecto — porque la metodología punkchainer's opera en 15-20x con SLs ajustados. Si una señal pide >20x, WARN al operador pero sin override automático (decisión consciente). En tier-0 MUGRE el cap baja a 3x (ver `rules.md` #11).
3. **Documentar SKIPS** — cada señal que rechaces va a `memory/signals_received.md`. Después puedes verificar si esa señal HUBIERA ganado (FOMO check).

## Setup inicial

```bash
# 1. Registro en Bitunix con código de referido
#    https://bitunix.com — usa código `punkchainer`

# 2. Depósito inicial $200 (vía USDT en BSC/Polygon, low fee)

# 3. Llenar credenciales en .env (NO necesarias para read-only):
#    BITUNIX_API_KEY=<...>           # solo si quieres tracking automático
#    BITUNIX_API_SECRET=<...>
#    BITUNIX_REFERRAL_CODE=punkchainer

# 4. Switch profile
/profile bitunix

# 5. Pre-sesión (NUEVO comando — antes de esperar señales Discord):
/punk-morning
# Ejecuta scan exhaustivo de 10+ assets, prepara Neptune en TV,
# valida macro events, lista DUREX/Saturday rules, muestra slots libres (X/2)

# 6. Cuando llegue señal Discord:
/signal <SYMBOL> <SIDE> <entry> sl=<sl> tp=<tp> leverage=<lev>

# 7. Cuando cierres posición:
/log-outcome <SYMBOL> TP1|TP2|TP3|SL <exit_price> [--pnl USD]
```

## Métricas a trackear

- **Hit rate de señales validadas** — de las que tu sistema aprueba, ¿cuántas son WIN?
- **Hit rate de señales rechazadas** — de las que SKIP, ¿cuántas hubieran sido WIN? (si >50%, tus filtros son demasiado restrictivos)
- **Comparativa vs replicar todo blindly** — si copias 100% sin filtrar vs filtrar con tu sistema, ¿cuál hubiera dado mejor PnL?
- **Outperformance vs solo retail** — ¿bitunix tiene mejor edge que tu sistema solo en BTC?

## Disclaimer

Las señales de la comunidad NO son consejo financiero. Tú decides ejecutar después de validar. El sistema NO ejecuta automáticamente.

> "El edge no es seguir gurús — es entender por qué su señal funciona (o no) y tener tu propia lógica para validar."
