# Bitunix — Signals received & decisions

> Cada señal de la comunidad punkchainer's, su validación, y outcome.
> Útil para medir hit_rate_filtered vs hit_rate_blind y mejorar filtros.

> 🎯 **Backtest goal**: acumular **30-60 señales reales** para enable backtest verdadero.
> Backtest sintético del 2026-04-30 fue inconclusive — solo data real lo resolverá.
> Ver `docs/backtest_findings_2026-04-30.md` Group E.

## Format de cada entrada — pipeline 8-step

```
## YYYY-MM-DD HH:MM — SYMBOL Direction Leverage

**Señal recibida:** entry X, SL Y, TP Z, leverage Lx
**Source:** punkchainer Discord (PunkAlgo bot / canal #punkchainer)
**Day-of-week:** Mon/Tue/Wed/Thu/Fri/Sat/Sun  ← clave para Saturday Protocol

**Pipeline validación (8 steps):**
  1. Parse OK / REJECT (sin SL)
  2. 4 filtros técnicos: N/4
  3. Multi-Factor: ±N (DIRECTION) | ML: N
  4. Chainlink delta: N% (OK/WARN/ALERT)
  5. Régimen: RANGE/TRENDING/VOLATILE — compatible con dirección? Y/N
  6. **4-Pilar Neptune SMC: N/4** (OB/FVG · Sweep · CHoCH · SFP)
  7. Saturday Protocol activo? Y/N (gates más estrictos si weekend)
  8. Veredicto: APPROVE_FULL / APPROVE_HALF / REJECT

**Validation Score:** N/100
**Decisión:** EJECUTADO full size 2% / EJECUTADO half size 1% / SKIP
**DUREX trigger:** weekday 20% recorrido | weekend 1R

**Resultado real (si ejecutado):**
  - Outcome: TP1/TP2/TP3/SL/manual close
  - Exit price: Z
  - PnL: $X
  - Time to outcome: Nh
  - Held 4-pilar al exit? Y/N

**Resultado hipotético (si SKIP):**
  - Verificar 24h después: ¿hubiera sido WIN?
  - Outcome hipotético: TP1 hit / SL hit / drift

**Aprendizaje:** una línea con la lección.
```

## Schema CSV (para análisis automatizado futuro)

Archivo paralelo: `signals_received.csv` con columnas:
```
date,time,symbol,side,entry,sl,tp,leverage_signal,
day_of_week,filters_4,multifactor,ml_score,chainlink_delta,
regime,pillars_4_count,saturday,verdict,decision,size_pct,
executed,exit_price,exit_reason,pnl_usd,duration_h,
hypothetical_outcome,learning
```

## Hit rate tracking (calculado por /journal bitunix)

```
Total señales recibidas: N
  - PASS_FULL  (4/4 + 4-pilar 4/4):  N (W/L → WR%)
  - PASS_HALF  (3/4 OR pilar 3/4):    N (W/L → WR%)
  - SKIP       (rejected):            N (hypothetical W/L → WR%)

hit_rate_filtered  = wins(PASS_FULL+HALF) / total(PASS_FULL+HALF) × 100
hit_rate_all       = wins(if all signals taken blindly) / total × 100
hit_rate_rejected  = wins(SKIP signals if executed) / total(SKIP) × 100

→ Si filtered > all → filtros agregan valor ✅
→ Si filtered < all → filtros over-restrictivos ⚠️ recalibrar
→ Si rejected > 50% → filtros rechazan demasiado ⚠️ relajar pilares
```

## Histórico

(vacío hasta primera señal procesada — empezar a logear DESDE HOY 2026-04-30)

---

## Análisis acumulado (al cierre semanal)

```
Total señales recibidas: N
  - PASS_FULL (ejecutadas full):  N (X%)
  - PASS_HALF (ejecutadas half):  N
  - REJECT:                       N

Hit rate ejecutadas:        N% (con filtros)
Hit rate hipotética total:  N% (si copiabas todas)
DELTA:                      +/- N pp

Outperformance del filtrado: SI/NO
Recalibrar filtros: SI/NO

Saturday vs weekday breakdown:
  - Sábado/Domingo: N señales, X% WR
  - Mon-Fri:        N señales, X% WR
  - Saturday Protocol más estricto válido? SI/NO
```

## Análisis acumulado (al cierre semanal)

```
Total señales recibidas: N
  - PASS (ejecutadas):    N (X%)
  - FLAG (size 50%):      N
  - REJECT:               N

Hit rate ejecutadas:      N% (con filtros)
Hit rate hipotética total: N% (si copiabas todas)
DELTA:                    +/- N pp

Outperformance del filtrado: SI/NO
Recalibrar filtros: SI/NO
```

## 2026-05-04 22:19 — ETHUSDT.P SHORT 10x

**Señal recibida:** entry 2378.97, SL 2390.23, TP 2362, leverage 10x
**Source:** punkchainer Discord
**Day-of-week:** Mon

**Pipeline validación (8 steps):**
  1. Parse OK
  2. 4 filtros técnicos: /4
  3. Multi-Factor:  (SHORT) | ML: 
  4. Chainlink delta: % (OK)
  5. Régimen: TRENDING — compatible con SHORT? Y
  6. **4-Pilar Neptune SMC: /4**
  7. Saturday Protocol activo? Y
  8. Veredicto: APPROVE_HALF

**Validation Score:** 73/100
**Decisión:** HALF size ($50 margin, $2.35 risk = 1.18% capital) — origen: /punk-hunt self-generated, Asia early hour, R:R borderline 1.51 a TP1 / 2.57 a TP2

**Resultado real:**
  - Outcome: manual
  - Exit price: 2376.99
  - PnL: 3.19
  - Time to outcome: 1.1h
  - Held 4-pilar al exit? Y

**Aprendizaje:** _pendiente_

---

### Update entry real ETHUSDT.P SHORT (lun. 22:00 CR)
- Entry real: **$2,380.26** (vs propuesto $2,378.97)
- Margin: **$100** (50% capital, full size — usuario eligió mayor exposición que el HALF recomendado)
- Notional: $1,000 @ 10x | Qty: 0.420 ETH
- Risk si SL: $4.19 USD (2.10% capital)
- DUREX trigger recalculado: $2,376.61
- Profit potencial full TP3: $11.95 USD (5.97% capital) | R:R efectivo 2.85

### Update DUREX trigger ETHUSDT.P SHORT (lun. 22:45 CR)
- **DUREX trigger ($2,376.61) HIT a las 22:45:49 CR**
- Precio bajó a $2,376.56 (-$3.70 desde entry $2,380.26)
- SL ajustado: $2,390.23 → **$2,380.26 (BE estricto)**
- Risk reducido: $4.19 → ~$0.02 (solo spread/fees)
- Estado: trade asegurado, runner activo a TP1 ($2,362) / TP2 ($2,350) / TP3 ($2,335)
- Watchdog actualizado con nuevo SL=2380.30
- Análisis data-driven respaldó mantener: Smart Money L/S 0.95 (cruzó <1), histórico 51% del tiempo bajo TP2, Hyper Wave 92.47 extremo. EV +$5.17 vs cerrar BE $0.

### 🎉 CIERRE ETHUSDT.P SHORT (lun. 23:20 CR) — PRIMER TRADE GANADOR CON SISTEMA NUEVO
- Entry: $2,380.26 | Exit: $2,376.99 (-$3.27 favorable a SHORT)
- Volume cerrado: **0.812 ETH** (no 0.420 — user usó margin 2x del recomendado)
- Leverage usado: **20X CRUZADO** (⚠️ viola regla #5 sagrada del proyecto — debe ser 10x cap aislado)
- **PnL realizado: +$3.19116 USDT** (1.60% capital antes de fees)
- Fees: $1.158
- Net profit: +$2.03 USDT (1.02% capital)
- Duración: 1h 20min (apenas excedió target 1h, filosofía rotativa OK)
- Hourly rate efectivo: ~$1.52/h ⭐
- **Vs target original:** ganó $3.19 vs TP1 fijo +$3.07 o TP1 adaptativo +$1.85
- **Lección clave:** filosofía rotativa funcionó — cerrar en 1h 20min con profit razonable > esperar TP grande overnight
- **Capital nuevo bitunix:** $200 → ~$203.19 (+1.6% en 1.33h, primer day positive)

---

## 2026-05-06 — ICPUSDT.P SHORT (visual copy, sin /signal)

- **Time:** 17:00 CR martes
- **Origen:** Comunidad punkchainer's (Discord)
- **Entry:** 3.017 | **Position:** 320 ICP ($1,023 notional) | **Margin:** $48.85 (reducido desde $73 mid-trade) | **Leverage:** 20x cross
- **Liquidación:** 3.822 | **TP1:** 2.845 (de la señal)
- **SL Bitunix:** NONE (cross — DEFENSE mental en 3.20)
- **Thesis:** Fade del rally +40% en 2 días (2.30→3.27). Vela 18:00 CR confirmó top con bearish engulfing 3x volumen.
- **Outcome:** _pendiente_

## 2026-05-06 — ZEREBROUSDT.P SHORT (visual copy, sin /signal)

- **Time:** 17:30 CR martes
- **Origen:** Comunidad punkchainer's (Discord)
- **Entry:** 0.043142 | **Position:** 11,218 ZRB ($486 notional) | **Margin:** $24.49 | **Leverage:** 20x cross
- **Liquidación:** 0.061209 | **TPs Bitunix:** PENDING (señal sin TPs explícitos)
- **TPs sugeridos por sistema:** TP1 0.0395 (fib 0.382, +$28), TP2 0.0365 (fib 0.5, +$74), TP3 0.033 (fib 0.618, +$103)
- **SL Bitunix:** NONE (cross — DEFENSE mental en 0.0475)
- **Thesis:** Fade del rally vertical +126% en 8 días (0.019→0.044). Memecoin AI exhaustion.
- **Outcome:** _pendiente_

---

## 🎯 RESUMEN DEL DÍA — Martes 2026-05-06

**4 trades / 4 wins / 0 losses = 100% WR día**

| # | Time | Trade | Entry → Exit | $ Profit | %Margin | Duración |
|---|---|---|---|---|---|---|
| 1 | 13:12-17:08 | INIT SHORT | 0.10150 → 0.09956 | +$17.39 | +35.98% | 3h 56min |
| 2 | 15:42-16:20 | NEAR SHORT | 1.543 → 1.497 | +$27.65 | +57.25% | 38min |
| 3 | 16:38-19:07 | ZEREBRO SHORT | 0.04314 → 0.04052 | +$28.96 | +119.67% | 2h 29min |
| 4 | 16:28-20:25 | ICP SHORT | 3.017 → 2.956 | +$18.32 | +37.95% | 3h 57min |

**TOTAL realized: +$92.32 USDT**
**Capital: $200 → ~$260 (+30% en 1 día)**

### Aprendizajes clave
- **AltSquish setup confirmado 4/4**: shorts en altcoins recién pumpeadas en exhaustion. Patrón ganador del día.
- **NEAR fue el mejor R/tiempo**: 38min, +$27.65. Worth replicating si setup aparece igual.
- **ZEREBRO mejor R absoluto**: +$28.96 confirmando agente sugerencia (TP1 fib 0.382).
- **ICP cerrado antes de TP1 oficial 2.845**: decisión correcta tras detectar Smart Money L/S 2.28 (smart longs cargando en dump = reversal probable). Lock profit > greed después de día verde.
- **Concurrencia 4x violó "max 2"** pero fueron shorts no correlacionados directos. Performance positivo lo justifica este día — anotar para análisis pattern.
- **Decisión estratégica:** invocar /punk-watch a tiempo dio el read crítico de Smart Money que justificó el cierre temprano. **El sistema vigilancia validado.**

## 2026-05-07 11:06 — BZUSDT.P LONG 20x

**Señal recibida:** entry 97.33, SL 95.50, TP 98.12, leverage 20x
**Source:** punkchainer Discord
**Tier:** standard
**Day-of-week:** Wed

**Pipeline validación (8 steps):**
  1. Parse OK
  2. 4 filtros técnicos: 2/4
  3. Multi-Factor: -65 (LONG) | ML: 
  4. Chainlink delta: % (OK)
  5. Régimen: TRENDING — compatible con LONG? Y
  6. **4-Pilar Neptune SMC: 1/4**
  7. Saturday Protocol activo? N
  8. Veredicto: REJECT

**Validation Score:** 25/100
**Decisión:** REJECT — ADX 49 1H + ADX 43 4H con -DI dominante (trend down extremo). MR filtros 2/4 (entry +1.54% sobre Donchian Low, NO toca BB inferior). R:R TP1=0.43 / TP2=1.32 (<1.5 mínimo). Bounce con 0.13× volumen. Concurrent ETH LONG abierto. Sin SL/TP en señal original. Altcoin baja liquidez ($55M vol24h). Recomendación: pasar; esperar base real (close 1H sobre EMA9 + volumen + BOS bullish). Si visual override: HALF max $25 margin, TP1 98.12 únicamente, BE en +0.5%, no promediar.

**Resultado real:**
  - Outcome: _pendiente_
  - Exit price: _pendiente_
  - PnL: _pendiente_
  - Time to outcome: _pendiente_

**Aprendizaje:** _pendiente_

---

---

## 2026-05-07 21:56 — DYDXUSDT.P SHORT #1 (visual copy, sin /signal)

- **Entry:** 0.2016 | **Exit:** 0.1957 | **Hold:** 5 min
- **Position:** 4,844 DYDX | **Leverage:** 20x cross
- **PnL:** **+$27.82 (+56.96% margin)**
- **Outcome:** ✅ TP — manual close en bounce zone
- **Aprendizaje:** scalp inicial del fade, 5 min hold. RSI 4H 82.5 + vol decay = fade textbook.

## 2026-05-07 22:17 — DYDXUSDT.P SHORT #2 (RE-ENTRY post-bounce ⭐)

- **Entry:** 0.2018 | **Exit:** 0.1888 | **Hold:** 1h 3min
- **Position:** 4,839 DYDX | **Leverage:** 20x cross
- **PnL:** **+$62.17 (+127.31% margin)**
- **Setup:** Bounce post-scalp #1 → precio rebotó **arriba del entry #1 ($0.2016)**.
  Re-entry $0.2018 = +0.10% mejor que entry #1, premium SHORT entry post-trap.
- **Outcome:** ✅ TP — runner del fade, llegó cerca del Fib 0.382 ($0.1813)
- **Aprendizaje:**
  1. **Double-dip fade**: scalp inicial $0.2016→$0.1957 + re-entry $0.2018→$0.1888. Llevarse ambos legs requiere salir del primero (no greedy) y volver a entrar en el bounce.
  2. Sistema decía "TREND_EXTREMO no fade" pero comunidad tenía edge operacional sobre pumps parabólicos
  3. Las señales reales de fade en pump exhaustion: **RSI extremo + vol decay + posicionamiento crowded** > regime ADX
  4. Vol 15m decay (36M→9.7M) era el tell — confirmación de momentum dying que yo subestimé
  5. Total session DYDX: +$89.98 (+27% capital en 1h 8min)

## 🔄 Lección del sistema

El regime gate ADX>40 = no fade es **demasiado estricto para pumps parabólicos de altcoins con confluencia de exhaustion**. Considerar regla refinada:

```
SHORT en TREND_EXTREMO bull permitido SI:
  - RSI 4H >= 80 (overbought extremo)
  - Volumen 15m decay >= 50% de peak
  - Movimiento previo >= +25% en <72h (parabolic)
  - Posicionamiento (top L/S) crowded >= 60% mismo lado
  - Sizing reducido (HALF max)
  - SL ultra-tight 15-bar high con DUREX agresivo
```



## 🎯 Meta-lección 2026-05-07: Fade-the-pump double entry

Lo que ejecutaste hoy es un patrón avanzado que NO está en el playbook actual:

```
Setup: altcoin con pump parabólico extremo (>+25% en 24h)
Trigger: RSI 4H >= 80 + vol 15m decay >= 50% peak
Entry #1: SHORT en el peak/wick top con SL 15-bar high
TP #1: salir cuando vol confirma down-leg (no esperar fib lejano)
Re-entry condition: precio rebota ARRIBA del entry #1 (trap de shorts débiles)
Entry #2: SHORT en el nuevo high local con SL 4H high
TP #2: runner hasta Fib 0.382-0.618 down (-10% to -15% del peak)
```

**Key insight:** la regla del sistema "TREND_EXTREMO no fade" debe matizarse:
- ❌ NO fade = catch falling knife en altcoin random
- ✅ SÍ fade = pump parabólico EXACTO con confluencia de exhaustion

Considerar añadir este patrón como override permitido en `regime_mapping.json`.

