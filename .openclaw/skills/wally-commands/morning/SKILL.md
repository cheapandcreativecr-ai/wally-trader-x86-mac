---
name: morning
description: Análisis matutino adaptado al profile activo
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
<!-- generated from system/commands/morning.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /morning -->


Análisis matutino adaptado al profile activo.

Pasos que ejecuta Claude:

1. Lee profile: `PROFILE=$(python3 .claude/scripts/profile.py get)`

2. SI profile == "retail":
   - Despacha `morning-analyst` (BTC-BingX single-asset, 17 fases, ver abajo)
   - El agente usa niveles/memoria de `profiles/retail/memory/`
   - **FASES TV OBLIGATORIAS** (ya documentadas en el agente):
     - FASE 11: dibujo completo (Donchian 15 + BB + PDH/PDL + Weekly Open + VWAP + Neptune 1D/4H + entry/SL/TP1/2/3 si setup)
     - FASE 11b: BIAS LONG/SHORT/NEUTRAL con trigger e invalidación
     - FASE 11c: watchlist 3-5 precios con alertas sugeridas

3. SI profile == "ftmo":
   - Despacha `morning-analyst-ftmo` (multi-asset, universo BTC/ETH/EURUSD/GBPUSD/NAS100/SPX500)
   - El agente analiza los 6 assets y selecciona 1 A-grade
   - Incluye guardian pre-check antes de proponer setups
   - Usa niveles/memoria de `profiles/ftmo/memory/`
   - **FASES TV OBLIGATORIAS** (ya documentadas en el agente):
     - FASE 11: cambio a TV symbol del asset ganador (mapeo OANDA/BINANCE) + dibujo S/R 4H + Donchian 1H + BB + PDH/PDL + entry/SL/TP1/2
     - FASE 11b: BIAS LONG/SHORT/NEUTRAL con trigger e invalidación (ajustado por correlación multi-asset y DXY)
     - FASE 11c: watchlist 3-5 precios con alertas sugeridas

4. SI profile == "fotmarkets":
   - Ejecuta validación previa:
     ```
     python3 .claude/scripts/fotmarkets_guard.py check
     ```
     Si BLOCK por ventana u otras razones → muestra el BLOCK pero continúa con análisis "preparativo" (sin entry sugerida).
   - Lee `.claude/profiles/fotmarkets/config.md` para obtener `phase` actual y `allowed_assets`
   - Despacha `morning-analyst-ftmo` con instrucción especial:
     - "Modo FOTMARKETS activado — seguir sección FOTMARKETS-AWARE del agente"
     - "Analizar SOLO los siguientes assets: <allowed_assets de la fase actual>"
     - "Usar reglas de Fotmarkets-Micro (NO FTMO-Conservative): filtros de strategy.md"
     - "Ventana operativa: CR 07:00-11:00 (no 06:00-16:00)"
     - "Risk per trade: <phase_risk_pct>% (phase-aware), cap $<phase_risk_usd_cap>"
     - "Max trades hoy: <phase_max_trades>"
     - "TF entry 5m / confirmación 15m / contexto 1H (no 4H)"
     - **"FASE TV OBLIGATORIA — cambiar chart a símbolo TV equivalente del asset elegido:"**
       - EURUSD → `OANDA:EURUSD` | GBPUSD → `OANDA:GBPUSD` | USDJPY → `OANDA:USDJPY`
       - XAUUSD → `OANDA:XAUUSD` | NAS100 → `OANDA:NAS100USD` | SPX500 → `OANDA:SPX500USD`
       - BTCUSD → `BINANCE:BTCUSDT` | ETHUSD → `BINANCE:ETHUSDT`
       - TF inicial 5m tras switch
     - **"FASE DIBUJO TV OBLIGATORIA — trazar con `draw_shape` en este orden:"**
       1. `horizontal_line` en **resistencia 1H** clave (color rojo) con label "R1H"
       2. `horizontal_line` en **soporte 1H** clave (color verde) con label "S1H"
       3. `horizontal_line` en **Donchian High/Low(20) 5m** (color naranja) con label "DC HI/LO"
       4. `horizontal_line` en **EMA50 15m** (color azul) con label "EMA50 15m"
       5. `rectangle` marcando **entry zone** (±0.15% del nivel estructural)
       6. `horizontal_line` en **SL** (color rojo grueso) con label "SL"
       7. `horizontal_line` en **TP (2R)** (color verde grueso) con label "TP 2R"
       8. Si NO hay setup A-grade → dibujar SOLO S/R + Donchian (vigilancia, sin entry)
     - **"FASE BIAS OBLIGATORIA — indicar dirección explícita:"**
       - 🟢 **BIAS LONG** si EMA50(15m) > EMA200(15m) AND precio cerca soporte
       - 🔴 **BIAS SHORT** si EMA50(15m) < EMA200(15m) AND precio cerca resistencia
       - ⚪ **BIAS NEUTRAL** si EMAs cruzadas/planas o precio en medio del range
       - Incluir **trigger condicional** ("si cierra 5m >X → confirma LONG", "si rompe <Y → invalida")
     - **"FASE WATCHLIST OBLIGATORIA — niveles a vigilar en TV:"**
       - Lista de 3-5 precios clave con acción asociada ("si toca X, revalidar filtros")
       - Sugerir alertas TV (`alert_create`) para:
         - Toque de soporte/resistencia clave
         - Break de EMA50 15m
         - Precio al edge del Donchian
   - El agente usa niveles/memoria de `profiles/fotmarkets/memory/`
   - Al final, recordatorio explícito:
     - "⚠️ Profile fotmarkets = bonus $30 en broker no regulado. Este no reemplaza tu profile FTMO/retail real."
     - "Verificar bonus T&C en memory/session_notes.md antes de ejecutar."
     - "Ejecución manual en MT5 — TV solo vigila, no ejecuta."

5. SI profile == "fundingpips":
   - Ejecuta validación previa OBLIGATORIA:
     ```bash
     python3 .claude/scripts/fundingpips_guard.py check --verbose
     ```
     Si BLOCK por ventana o reglas duras → muestra el BLOCK + continúa análisis preparativo SIN entry sugerida.
   - Despacha `morning-analyst-ftmo` con instrucción especial:
     - "Modo FUNDINGPIPS activado — sigue las reglas de `.claude/profiles/fundingpips/strategy.md` (FundingPips-Conservative)"
     - "Universo MULTI-ASSET 20+: forex (EURUSD/GBPUSD/USDJPY/USDCHF/AUDUSD/USDCAD/NZDUSD + crosses) + indices (NAS100/SPX500/US30/GER40/UK100/JPN225) + crypto (BTCUSD/ETHUSD) + commodities (XAUUSD/XAGUSD)"
     - "Risk per trade: 0.3% del capital ($30 sobre $10k) — NO 0.5% como FTMO"
     - "Target diario: 0.5-0.7% (consistency-friendly, NO 1.5% FTMO)"
     - "Max trades hoy: 2 (NO 3 como FTMO)"
     - "TP fijo (NO trailing) — incompatible con regla 15% consistency"
     - "Daily loss BLOCK en -2% (oficial -3%); Total DD BLOCK en -3% (oficial -5%)"
     - "Plataforma MT5 con server FundingPips-Live (mismo EA bridge que FTMO, magic 88888)"
     - **"FASE PRE-SCAN: ejecutar `/multifactor` en cada asset candidato + `/risk-var --target-var-pct 0.5` para sizing"**
     - **"FASE SELECCIÓN A-grade: pick 1 asset con multifactor>+50 (long) o <-50 (short) + ML score >55 + Chainlink OK"**
     - **"FASE TV OBLIGATORIA — cambiar chart al símbolo TV del ganador (mapeos OANDA/BINANCE/TVC)"**
     - **"FASE BIAS: indicar BIAS LONG/SHORT/NEUTRAL con trigger condicional explícito"**
     - **"FASE WATCHLIST: 3-5 precios con alertas TV sugeridas"**
   - Al final, recordatorio explícito:
     - "⚠️ FundingPips Zero = dinero real. $99 perdido si rompes 5% DD. NO operar setups de baja convicción."
     - "Verificar status en `.claude/profiles/fundingpips/memory/session_notes.md` antes de ejecutar."
     - "Ejecución manual en MT5 (login FundingPips-Live)."

6. Si argumento opcional: pasa como contexto adicional al agente (ej: "/morning sin café")

## Fases del morning-analyst retail (17 fases, incluye Pre-flight TV)

0. **Pre-flight TV** — `tv_health_check`; si está cerrado → `tv_launch` (auto `--remote-debugging-port=9222`), espera 10s, re-verifica. Valida símbolo = BINGX:BTCUSDT.P.
1. Auto-check personal (sueño, comida, estado mental)
2. Contexto global (F&G, funding, on-chain, sentiment)
3. Correlaciones (ETH, SPX, DXY)
4. Noticias / eventos próximas 6h
5. Detección de régimen (4H + 1H)
6. Selección de estrategia
7. Niveles técnicos multi-TF
8. Money flow + patrones (incluye FASE 8.5: Bookmap orderflow manual, solo retail/Binance — https://web.bookmap.com/)
9. Position sizing con capital actual
10. Dibujo en TradingView (limpia + redibuja)
11. Plan de entrada (entry, SL, TP1/2/3)
12. Checklist pre-entry (12+ items)
13. Reglas duras recordatorio
14. VEREDICTO FINAL

Si hay argumentos, úsalos como contexto adicional:
$ARGUMENTS
