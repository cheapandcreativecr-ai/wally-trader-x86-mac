# Reglas Bitunix Copy-Validated

> Filosofía: el edge no es seguir señales — es **rechazar las malas**.

## 1. RISK PER COPIED SIGNAL — 2% del capital

**Cálculo:** `risk_usd = capital × 0.02`

Capital actual $200 → max loss $4.00 per signal.

## 1b. MAX MARGIN PER TRADE — 30-35% del capital (NUEVA 2026-05-04)

**Lección aprendida del primer trade real:** entré con margin $100 (50% capital) — demasiado concentrado para filosofía rotativa. Si 2 trades simultáneos a 50% cada uno = 100% capital expuesto, sin margen para tercer setup.

**Nueva regla:** max margin por trade = **30-35% del capital** = $60-70 sobre $200.

| Modalidad | Margin | Notional @ 10x | Risk si SL |
|---|---|---|---|
| Conservador | $50 (25%) | $500 | $2.10 (1.05%) |
| **Estándar** ⭐ | **$60 (30%)** | $600 | $2.52 (1.26%) |
| Agresivo | $70 (35%) | $700 | $2.94 (1.47%) |
| **❌ BLOCK** | **>$70** | >$700 | viola la regla |

Ventajas:
- Permite 2 trades concurrentes (60+60=120, queda $80 disponible)
- Risk USD por trade ~$2.50 (no llega a 2% target completo, más conservador)
- 3 SLs → -$7.56 (4% capital) — bien dentro del cap diario -6%

## 1c. TIME-OUT POR TRADE — 90 min sin TP1 hit (NUEVA 2026-05-04)

Filosofía rotativa: si trade no genera profit en 90 min → liberar slot para próximo.

| Tiempo elapsed | Acción |
|---|---|
| 0-30 min | OK normal — esperar movimiento |
| 30-60 min | Correr `/punk-watch` para verificar contexto |
| 60-90 min | **WARN**: re-evaluar TPs adaptativos vs originales, considerar cierre parcial |
| **>90 min sin TP1 hit** | **CIERRE FORZADO** o ajuste explícito de TPs vía /punk-watch |

**Excepción:** si `/punk-watch` recomienda explícitamente "AGUANTAR" (ej. catalyst próximo en 1-2h, contexto fortaleciendo) → puede excederse hasta 4h máx.

| Nivel | Trigger | Acción |
|---|---|---|
| **APPROVE** | Risk ≤ 2% | Ejecutar |
| **REJECT** | Risk > 2% (señal pide más) | NO copiar — ajustar size local hasta cumplir 2% |

## 2. MAX COPIED SIGNALS POR DÍA — 10 (recalibrado 2026-05-04)

Cambio: 7 → 10 trades/día para soportar filosofía rotativa "1 trade/hora".

Con ventana operativa CR 06:00-23:00 (~17h), 10 trades = 1 cada ~1.7h promedio. Espacio
para tomar setups B-grade además de A-grade cuando contexto débil. WR target ~65-70% =
6-7 wins + 3-4 losses = +EV consistente.

| Nivel | Trigger | Acción |
|---|---|---|
| **OK** | 0-7 trades hoy | OK siguiente |
| **WARN** | 8-9 trades hoy | "Quedan 1-2 espacios — selectivo, A-grade only" |
| **BLOCK** | 10 trades hoy | Skip resto del día |

## 2b. MAX CONCURRENT OPEN POSITIONS — 2

Independiente del cap diario, **nunca más de 2 posiciones abiertas simultáneamente**.

| Slots usados | Trigger | Acción |
|---|---|---|
| **OK** | 0/2 ó 1/2 abierta | Recibir nueva señal normal |
| **BLOCK** | 2/2 abiertas | SKIP nueva señal hasta cerrar 1 con `/log-outcome` |

Conteo desde `signals_received.csv` (entries con `outcome = _pendiente_`).

## 3. MIN VALIDATION SCORE — 60%

**Compositición del score (0-100):**
- 4/4 filtros técnicos: 25 puntos
- Multi-Factor en dirección: hasta 25 puntos (proporcional al |score|)
- ML XGBoost en dirección: hasta 25 puntos
- Régimen compatible: 15 puntos
- Chainlink valida: 10 puntos

| Nivel | Trigger | Acción |
|---|---|---|
| **MAX_GO** | Score ≥80 | Ejecutar size full (2%) |
| **GO** | Score 60-80 | Ejecutar size full (2%) |
| **FLAG** | Score 50-60 | Ejecutar size HALF (1%) — borderline |
| **REJECT** | Score <50 | SKIP — log a signals_received.md |

## 4. LEVERAGE CAP — 20x (excepción profile-específica del cap 10x global)

Bitunix sigue al leverage de la señal hasta **20x**. Esta es la excepción declarada del cap 10x global del proyecto, justificada por la metodología punkchainer's: entries con SLs ajustados a estructura SMC + Reversal Bands → la liquidación a 20x rara vez se toca antes que el SL de la señal.

| Señal pide | Tu ejecutas | Comentario |
|---|---|---|
| 5x | 5x (igual) | low conviction acceptable |
| 10x | 10x (igual) | conservador |
| 15x | 15x (igual) | normal |
| 20x | 20x (igual) | normal — leverage típico de la comunidad |
| 25-50x | **WARN** | calcula distancia a liquidación; ejecución es decisión consciente, no override automático |
| >50x | **REJECT** | absurdo, no hay setup que justifique |
| Sin SL | **REJECT** | regla #1 — sin SL no se evalúa leverage |

**Excepciones a este cap (más estrictos):**
- **Tier-0 MUGRE:** 3x cap hard (regla #11)
- **Saturday/Sunday alts:** 5x cap (Saturday Precision Protocol)
- **Asset blacklisted (#7):** 0x — no entry permitido

## 5. DAILY LOSS BLOCK — 3 SLs (≈-6% = $12 sobre $200)

| Trigger | Acción |
|---|---|
| 1 SL hoy | Continuar normal |
| 2 SLs hoy | **WARN**: "Cuidado, próxima decisión es la última del día" |
| 3 SLs hoy (~-$12) | **BLOCK**: STOP día. No más copia hasta mañana. |

## 6. MAX DD DEL CAPITAL — 30%

Si tu equity cae a 70% del capital de start de profile ($140 si empezaste con $200):
- **STOP**: cerrar profile, hacer review
- Posibles causas: filtros mal calibrados, comunidad en mal momento, leverage demasiado agresivo
- Recomendación: pausar 1 semana + revisar `signals_received.md` para encontrar patrón

## 7. AUTO-BLACKLIST ASSET — 2 SLs consecutivos

Si el mismo asset (ej. MSTRUSDT) te da 2 SLs consecutivos en la misma semana:
- Auto-blacklist por 7 días
- No copiar señales de ese asset aunque la comunidad las publique
- Razón: probablemente el asset está en régimen no-tradeable temporalmente

## 8. ASSET CONFLICT CROSS-PROFILE

| Si ya tienes posición ABIERTA en... | Y la señal Bitunix es de... | Acción |
|---|---|---|
| retail BTC | BTC perpetual | **REJECT** — doble exposición |
| ftmo BTCUSD | BTCUSDT.P | **REJECT** |
| fundingpips BTCUSD | BTCUSDT.P | **REJECT** |
| quantfury BTC | BTCUSDT.P | **REJECT** |
| retail BTC | ETH (correlado +0.85) | **WARN** — correlación alta |
| retail BTC | EURUSD (no correlado) | OK |

Sistema chequea con `pending_orders.json` y `mt5_state.json` de los demás profiles.

## 9. TIME WINDOW — preferir London/NY overlap

Aunque cripto es 24/7, el flujo institucional está en London/NY overlap (CR 06:00-15:00).

| Hora CR | Acción |
|---|---|
| 06:00-15:00 | **OK** — ventana óptima |
| 15:00-20:00 | OK con menor convicción (NY tarde) |
| 20:00-24:00 | WARN — Asia early, vol cae |
| 00:00-06:00 | **REJECT** — Asia death zone, evitar copy |

## 10. SIGNAL EXPIRY — 4 horas max

Si la señal apareció hace >4h, es "fuera de timing":
- El precio ya se movió (entry de la señal puede no ser válido)
- Liquidez puede haber cambiado
- **REJECT** — esperar próxima señal o pasar al día siguiente

## 11. MUGRE TIER-0 — reglas estrictas (NUEVA 2026-05-05)

Aplica solo cuando `/punk-hunt --tier-0` propone una entry sobre el subset MUGRE
(meme/low-cap del canal `mugre-signals` punkchainer's: BIO, PENDLE, RAVE, BSB, BASED,
OPG, BROCCOLI, BANANA, POWR — ver `config.md` tabla TIER 0 MUGRE).

**No aplica a `/signal` Discord:** señales externas mantienen reglas standard. El usuario
decide manualmente si baja leverage al ver el símbolo en la señal.

| Regla | Standard (24 assets) | **TIER 0 MUGRE** |
|---|---|---|
| Min score | 60% | **80%** |
| Max leverage | 10x | **3x** (override hard) |
| Max margin | 30% capital ($60) | **15% capital ($30)** |
| Risk per trade | 2% ($4) | **1% ($2)** |
| DUREX trigger | 20% recorrido TP1 | **1R** (mismo umbral que Saturday Protocol) |
| Concurrent slots | 2/2 totales | comparte el mismo counter |
| Daily cap | 10 trades | comparte el mismo counter |
| CSV `tier` field | `standard` | **`mugre`** |

**Razón:** liquidez frágil + slippage estructural alto destruye el edge a sizing normal.
A 3x con SL 2% = -$0.60 si liquida (vs -$2 a 10x). Risk asimétrico OK porque memes
pueden hacer +10-20% rápido cuando van — pequeñas pérdidas con upside intacto.

**Re-validar listings** (mensual o cuando `/punk-hunt --tier-0` reporta errores de símbolo):
```bash
python3 .claude/scripts/bitunix_pairs_check.py --tier 0
```

**Auto-blacklist (regla #7) aplica con criterio más estricto:** si un asset MUGRE da
**1 SL** (no 2) → blacklist 7d en el subset. Razón: volatilidad extrema implica que un
SL puede ser señal del régimen, no random. Asset standard sigue con threshold 2 SLs.

## Order de checks pre-execución

```
1. Profile == bitunix? → si no, este flow no aplica
2. Daily counter <7? → si no, BLOCK
3. Concurrent open <2? → si no, BLOCK (esperá a cerrar una)
4. Daily PnL > -6% ($12)? → si no, BLOCK
5. Total DD > -30% ($60)? → si no, BLOCK PROFILE
6. Asset no blacklisted? → si no, BLOCK
7. Sin conflict cross-profile? → si no, REJECT
8. Hora dentro ventana? → si no, WARN/REJECT según hora
9. Señal <4h vieja? → si no, REJECT
10. Validation score ≥50? → si no, REJECT
11. Leverage de la señal ≤20x (o ≤3x en tier-0 MUGRE, ≤5x en sábado/domingo)? → si >20x, WARN al operador
12. Macro events gate (`macro_gate.py --check-now`) NO bloqueado? → si bloqueado, NO-GO

→ TODOS OK → APPROVE con size según score
```
