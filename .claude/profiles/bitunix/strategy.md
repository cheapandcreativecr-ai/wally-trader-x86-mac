# Estrategia: Bitunix Copy-Validated

> No generas. Validas. Copias selectivamente.

## Parámetros core

| Parámetro | Valor | Razón |
|---|---|---|
| **Filosofía operativa** | **1 trade/hora rotativo** | Capturar lo que da el mercado en ventanas cortas, no esperar el "trade del día" |
| Risk per signal | **2%** ($4.00 sobre $200) | Mismo que retail |
| **Max margin per trade** | **30-35% capital** ($60-70 sobre $200) | Anti-concentración, permite 2 trades concurrentes con margen |
| Max leverage | **20x** | Sigue al leverage de la señal (excepción del cap 10x global). >20x = WARN, no override automático |
| Max signals/día | **10** (era 7, recalibrado) | Soporta filosofía rotación 1/h × 10-17h ventana |
| Max concurrent open positions | **2** | No diluir atención en >2 setups simultáneos |
| **Time-out por trade** | **90 min sin TP1 hit → cerrar manual o ajustar TPs** | Anti-overstay (filosofía rotativa) |
| **TP target alcanzable en** | **<60 min según ATR + context** | Filter en /punk-hunt: si TP1 requiere >60min → REJECT |
| Min validation score | **70%** (4 confluencias Elite Crypto + Hyper Wave) | Gate hard (más estricto que /signal 60% por ser self-generated) |
| Daily loss BLOCK | **-6%** ($12 sobre $200, ~3 SLs) | STOP día |
| Min lookback antes de copiar | 1 hora | Si la señal es muy reciente, espera 1h para validar que no fue hyped |

## Pipeline de validación (cada señal)

Cuando aparece una señal de la comunidad:

### Paso 1: Parse de la señal
Extraer: SYMBOL, SIDE, entry_price, SL, TP, leverage.
Si la señal no incluye SL → **REJECT inmediato** (no copiar señales sin SL definido).

### Paso 2: 4 filtros técnicos (`/signal` agent)
- ¿RSI compatible con la dirección? (LONG → RSI<35, SHORT → RSI>65)
- ¿Donchian band toque? (LONG → low(15), SHORT → high(15))
- ¿BB toque?
- ¿Vela cierra en dirección señal?

Si <4/4 → REJECT.

### Paso 3: Multi-Factor + ML cross-validation
```bash
# En el TF base del asset (15m default)
/multifactor                  # debe ser >+50 (long) o <-50 (short)
/ml --side <signal_side>      # debe ser >55
```

Si multifactor o ML divergen de la señal → **flag** ("la comunidad ve algo que tu sistema no ve").
Si MF >70 + ML >65 → **MAX conviction**, ejecutar.

### Paso 4: Chainlink cross-check (cripto only)
```bash
/chainlink <SYMBOL>           # delta vs entry señal <0.5%
```
Si delta >1% → **REJECT** (señal con feed stale o exchange-specific).

### Paso 5: Régimen + sentiment
- `/regime` debe ser compatible con dirección (no SHORT en TRENDING UP fuerte)
- `/sentiment` extremo contrarian → flag pero NO bloqueo

### Paso 6: 4-Pilar Neptune SMC checklist (visual manual)

Sobre el chart con Neptune SMC cargado, verifica los 4 pilares de la comunidad
(ver skill `@punkchainer-playbook` para definición completa):

**LONG:** Bullish OB/FVG + SSL Touched/Bullish Raid + Bullish CHoCH + Bullish SFP
**SHORT:** Bearish OB/FVG + BSL Touched/Bearish Sweep + Bearish CHoCH + Bearish SFP

```
4/4 pilares  → APPROVE max conviction (size 2%)
3/4 pilares  → APPROVE half size (1%)
<3/4 pilares → REJECT (regla "Baja Probabilidad")
```

⚠️ **Filtro Adjusted:** un CHoCH marcado solo por mecha sin cuerpo de cierre **NO es válido**.

### Paso 7: Saturday Precision Protocol (sábado/domingo)

Si fecha == sábado/domingo, gates más estrictos (ver `@punkchainer-playbook`):
- Pillars **4/4 obligatorio** (no 3/4)
- Leverage en alts **5x cap** (más estricto que el 20x weekday — viernes/sábado/domingo low-vol amplifica wicks)
- DUREX trigger acelerado: **1R** (no 20% recorrido)
- Solo entries Limit "sniper" (no market)
- BTC dump → 🚫 0 longs en alts low-cap
- Macro news → STAND-ASIDE total

### Paso 8: Veredicto final
```
PASS_ALL_GATES (≥60% confidence + 4-pilar OK) → EJECUTAR con tu sizing y leverage de la señal (max 20x cap)
FLAG (50-60% confidence O 3/4 pilares) → ejecutar con HALF size (1% en vez de 2%)
REJECT (<50% confidence O <3/4 pilares O Saturday rule violation) → SKIP, anotar razón
```

## Sizing canónico

```bash
# Asume señal: MSTRUSDT short, entry 166.57, SL 170 (2.06% adverso)
# Capital: $200, risk 2% = $4.00 max loss

# Cálculo (con leverage 20x de la señal):
# - SL distance: |170 - 166.57| / 166.57 = 2.06% (señal pide SL en 170)
# - Notional max @ 20x: $4.00 / 0.0206 = $194.17 (igual notional, menor margin)
# - Margin used: $194.17 / 20 = $9.71 (4.85% del capital)
# - Qty MSTRUSDT: $194.17 / 166.57 = 1.166 unidades

/signal MSTRUSDT short 166.57 sl=170 tp=160 leverage=20
# → Sistema dice: "OK con leverage 20x (señal). Size 1.166 MSTRUSDT, margin $9.71"
```

## Concurrencia (regla NUEVA)

**Max 2 posiciones abiertas simultáneamente.** El sistema cuenta entries en
`signals_received.csv` con `outcome = _pendiente_`.

| Slots usados | Acción al recibir nueva señal |
|---|---|
| 0/2 | OK — ejecutar normal |
| 1/2 | OK — ejecutar normal, recordar slot único restante |
| 2/2 | **BLOCK** — esperar a cerrar una con `/log-outcome` antes de abrir nueva |

Razón: con risk 2% × 2 trades = 4% expuesto (peor caso), suficiente para 1 cripto día estándar.
Más concurrencia = mayor correlación intra-cripto y menor atención por trade.

## 🛡 DUREX — regla obligatoria comunidad punkchainer's

> *"Sin globitos no hay fiesta. La prioridad número uno no es ganar dinero, es no perderlo."*

**Acción obligatoria post-entry:**

Después de ejecutar el trade copiado, mueve el SL al punto de entrada (Break Even) en el momento EXACTO que ocurra lo primero:
- **20% del recorrido a favor** hacia TP1, O
- **TP1 hit**

```
Ejemplo:
  Entry SHORT MSTRUSDT @ 166.57
  TP1 @ 160.00 (distance: 6.57 puntos)
  20% del recorrido = 6.57 × 0.20 = 1.31 puntos
  → Precio "DUREX trigger" = 166.57 - 1.31 = 165.26
  
  Cuando precio toca 165.26 (o TP1 si llega antes):
    → MOVER SL a 166.57 (entry)
    → Trade asegurado: máximo cierra en BE
```

**Por qué obligatorio en bitunix:**
- Es la regla #1 de la comunidad punkchainer's
- Protege capital cuando copy-trading (donde tu validación es secundaria a la del autor original)
- Si la señal falla, máximo pierdes spread + fee, no el risk completo

**Variante weekend (sábado/domingo):**
DUREX trigger se acelera de "20% recorrido O TP1" → **"1R (1:1) O TP1"** porque los wicks
sabatinos retornan a entry mucho más frecuente. Ver Saturday Precision Protocol en
skill `@punkchainer-playbook` (paso 7 del pipeline).

Ver skill `@punkchainer-glossary` para definición oficial completa.

## Leverage policy (profile-specific)

Bitunix sigue al leverage de la señal hasta **20x cap**. Es excepción del cap 10x global del proyecto, justificada por la metodología punkchainer's (entries con SLs ajustados a estructura SMC + Reversal Bands → la liquidación a 20x rara vez se toca antes que el SL de la señal). Reglas:

- **≤20x:** ejecutar al leverage que diga la señal sin warning.
- **>20x:** WARN al operador con cálculo de distancia a liquidación; ejecución es decisión consciente, no override automático.
- **Tier-0 MUGRE (low-cap alts del subset opt-in):** cap **3x** hard (ver `rules.md` #11). La volatilidad y liquidez frágil hacen que 20x liquide en wicks normales.
- **Saturday/Sunday alts:** cap **5x** (Saturday Precision Protocol). Low volume amplifica wicks.
- **Sin SL en la señal:** REJECT antes de evaluar leverage. No copiar señales sin SL definido.

## Cuándo NO copiar (filtros adicionales)

**REJECT automático si:**
- La señal aparece >4 horas después de la entry price → "fuera de timing"
- La señal es de un altcoin con liquidez <$5M 24h → riesgo de wick
- Asset ya operado HOY en bitunix → max 7 trades/día rule
- **Ya tenés 2 posiciones abiertas (slots 2/2 lleno) → SKIP nueva señal hasta cerrar una**
- Asset operado en retail/ftmo/fundingpips/quantfury HOY → doble exposición
- Daily PnL ≤ -6% ($12 sobre $200, ~3 SLs) → STOP día
- Total DD ≤ -30% del capital → STOP profile + review

**FLAG (size 50%) si:**
- Multifactor está entre +30 y +50 (borderline)
- ML score entre 45 y 55
- Chainlink delta entre 0.3% y 1% (WARN)
- Sentiment extremo contrarian a la señal

## Tracking de señales recibidas

Cada señal vista (haya sido copiada o rechazada) va a `memory/signals_received.md`:

```markdown
## 2026-04-30 09:35 — MSTRUSDT Short 20x

**Señal:** entry 166.57, SL 170, TP 160, lev 20x
**Mi sistema dice:** PASS (4/4 filtros, MF +62, ML 68, CL OK)
**Decisión:** EJECUTAR con leverage 20x (señal)
**Resultado:** TP1 hit en 165.61 → +$0.45 (después de fee)
**Aprendizaje:** flow MSTR-correlated funcionó como esperado
```

Esto te da feedback histórico para mejorar tus filtros.

## Outperformance metric (clave)

```
hit_rate_filtered  = wins / (wins + losses) de SEÑALES QUE TU SISTEMA APROBÓ
hit_rate_all       = wins / (wins + losses) si copiaras TODAS las señales blindly
hit_rate_rejected  = wins / (wins + losses) de las que RECHAZASTE (si fueran ejecutadas)

Si hit_rate_filtered > hit_rate_all → tus filtros agregan valor
Si hit_rate_filtered < hit_rate_all → tus filtros son demasiado restrictivos (paradoja)
Si hit_rate_rejected > 50% → estás rechazando demasiado, recalibra
```

Calculado por `/journal bitunix` automáticamente.

## Comparación con otros profiles

| Concepto | retail (Binance) | bitunix (copy) |
|---|---|---|
| Origen señal | Tu propio análisis | Comunidad punkchainer's |
| Universo | Solo BTCUSDT.P | Lo que ellos señalen |
| Filosofía | Generar edge | Filtrar el ruido |
| Risk per trade | 2% | 2% |
| Max trades/día | 5 | 7 |
| Concurrent positions | sin cap (1 asset) | max 2 simultáneas |
| Leverage | 10x | 20x cap (sigue señal) |
| Métrica clave | WR + PnL | hit_rate_filtered vs hit_rate_all |
