---
name: risk
description: Calcula position sizing según el profile activo
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
<!-- generated from system/commands/risk.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /risk -->


Calcula position sizing según el profile activo.

Pasos que ejecuta Claude:

1. Lee profile: `PROFILE=$(python3 .claude/scripts/profile.py get)`

2. SI profile == "retail":
   - Usa regla clásica 2% del capital actual (desde profiles/retail/config.md)
   - Despacha al agente `risk-manager` con parámetros retail
   - Fórmula: `risk_usd = capital * 0.02; size = risk_usd / (sl_distance / entry) / leverage`

3. SI profile == "ftmo":
   - Carga config desde `.claude/profiles/ftmo/config.md` (risk_per_trade_pct, leverage)
   - Lee equity actual via `python3 .claude/scripts/guardian.py --profile ftmo --action status`
   - Lee pip_value del asset desde `.claude/profiles/ftmo/memory/mt5_symbols.md`
   - Si pip_value es "PENDING" → ERROR: "Pip value de <asset> no validado. Pega screenshot MT5 Specification."
   - Fórmula:
     ```
     risk_usd = equity * (risk_per_trade_pct / 100)  # 0.5% por default
     sl_pips = abs(entry - sl)
     lots = risk_usd / (sl_pips * pip_value_per_lot)
     lots = round(lots, 2)
     ```
   - Simula worst-case en guardian:
     `python3 guardian.py --profile ftmo --action check-entry --asset <X> --entry <E> --sl <SL> --loss-if-sl <risk_usd>`
   - Si guardian retorna BLOCK_SIZE → aplica size_adjustment factor
   - Si BLOCK_HARD → NO-GO total

3.5. SI profile == "fotmarkets":
   - Lee capital actual: `CAP=$(python3 .claude/scripts/fotmarkets_phase.py capital)`
   - Detecta fase: `PHASE=$(python3 .claude/scripts/fotmarkets_phase.py)`
   - Mapea fase → risk_pct y risk_usd_cap:
     - Fase 1: risk_pct=10, cap=$3.00
     - Fase 2: risk_pct=5, cap=null (dinámico)
     - Fase 3: risk_pct=2, cap=null (dinámico)
   - Fórmula:
     ```
     risk_usd = min(CAP * risk_pct / 100, risk_usd_cap if set else infinity)
     sl_pips = abs(entry - sl) en pips del asset
     
     # pip value por 0.01 lot (referencia, VALIDAR con MT5 Specification del broker):
     #   EURUSD, GBPUSD, USDJPY: $0.10 por pip
     #   XAUUSD: depende del broker (típicamente $0.10 o $1.00 por pip)
     #   NAS100, SPX500: depende del broker (típicamente $0.10 por point)
     #   BTCUSD, ETHUSD CFD: depende del broker, usar Specification
     
     lots = risk_usd / (sl_pips * pip_value_per_lot)
     lots = floor(lots * 100) / 100  # redondeo 2 decimales hacia abajo
     
     if lots < 0.01 → ABORTAR con mensaje:
       "Trade imposible: sizing calculado ${lots} < min lot 0.01. Amplia SL o espera Fase N."
     ```
   - Valida asset en whitelist de la fase:
     ```
     if asset NOT IN phase_N.allowed_assets → ERROR "Asset <X> no desbloqueado hasta Fase Y"
     ```
   - Valida que trade sea viable con el Lite Guardian:
     ```
     python3 .claude/scripts/fotmarkets_guard.py check
     ```
     Si BLOCK → comunicar razón y sugerir posponer.

4. Output:
   - Lots (FTMO) o BTC size + margin (retail)
   - Capital a arriesgar ($X)
   - Leverage
   - Guardian veredicto (solo FTMO)

5. Siempre incluye disclaimer: "Leverage con dinero real puede liquidar capital. Tu decides."

Contexto del trade:
$ARGUMENTS
