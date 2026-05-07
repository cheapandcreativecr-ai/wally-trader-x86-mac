# 🌭 Wally Trader — Triple-Profile Trading System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-113%20passing-brightgreen.svg)](#)
[![Multi-CLI](https://img.shields.io/badge/harness-Claude%20Code%20%7C%20OpenClaw%20%7C%20OpenCode%20%7C%20Hermes-blue.svg)](#)
[![Memory](https://img.shields.io/badge/memory-Local%20%7C%20Notion%20%7C%20Hybrid-purple.svg)](#)

> Nombrado en honor a **Wally**, perro salchicha y CEO mascota del proyecto.

Sistema de trading algorítmico-asistido **triple-profile**: retail BingX BTCUSDT.P, FTMO MT5 multi-asset, y Fotmarkets bonus micro-capital. Construido sobre TradingView + Claude Code + Pine Script + MQL5 EA.

**Autor:** [Francisco Campos Diaz (@sasasamaes)](https://github.com/sasasamaes) · **License:** [MIT](LICENSE) · **Contribuciones:** ver [CONTRIBUTING.md](CONTRIBUTING.md)

**Status actual:** Retail validado con 3 wins (+36.3% / $10 → $13.63). FTMO profile + MT5 bridge implementados. **Bitunix profile activo $200 con suite adaptativa completa** (`/punk-morning`, `/punk-hunt`, `/punk-watch` + scoring 4 confluencias Elite Crypto + TPs/SL adaptativos al contexto).
**Objetivo:** Escalar retail $10 → $100, pasar challenge FTMO $10k fundeado, y ejecutar 1 trade/hora rotativo en bitunix capturando $20-100/día con WR ~70%.

---

## 🎯 Qué es este proyecto

Un **sistema operativo de trading** dual-profile que combina:

- **Dual profile aislado** — retail (BingX $13.63, Mean Reversion 15m) y FTMO ($10k demo, FTMO-Conservative multi-asset)
- **Guardian rules engine** — enforce automático de reglas FTMO (3% daily hard, 10% trailing warn, Best Day info)
- **MT5 Bridge** — manual-asistido o via ClaudeBridge.mq5 EA (file-based JSON bridge para macOS)
- **Estrategias validadas** — Mean Reversion + Donchian Breakout (retail) / FTMO-Conservative multi-asset (FTMO)
- **Indicador Pine Script** con los 4 filtros de entrada automatizados
- **Protocolo matutino** (retail 17 fases / FTMO 14 fases multi-asset)
- **Memoria aislada por profile** — trades FTMO no contaminan log retail y viceversa
- **Journal obligatorio** de cada trade + review semanal
- **Integración con TradingView** via MCP (Claude dibuja niveles, detecta señales)
- **Capa ML** (NLP sentiment + XGBoost supervisado) como 5° filtro opcional
- **Watcher autónomo "set & forget"** — `/order` programa entry virtual, launchd vigila cada 1h, escala a Claude headless cuando precio está cerca, notifica macOS al dispararse trigger
- **Multi-CLI portable** — canonical `system/` con 5 adapters: **Claude Code** · **OpenClaw** (con OpenRouter opt-in) · **OpenCode** · **Hermes** (Telegram/Discord/Slack) · Codex (untested)
- **Memoria unificada cross-harness/cross-device** vía Notion MCP — abrir CC en la mañana, OC en la tarde, Hermes/Telegram desde el celular, todos ven el mismo estado

No es un bot automatizado. Es una **disciplina acompañada** — Claude hace el análisis pesado, el guardian aplica reglas, tú ejecutas.

---

## 🚀 Instalación rápida — un solo prompt por harness

Pegá el prompt correspondiente en el agente que estés usando. El agente clona el repo, instala dependencias, configura el adapter y corre el smoke test. Tarda ~2-3 minutos.

> **Prerequisitos comunes:** Python 3.11+, Node 22+ (para los MCPs), `git`, `make`, [`uv`](https://github.com/astral-sh/uv) (para gestión del venv). En macOS: `brew install python@3.13 node uv`.

### 🤖 Claude Code

```
Por favor instalá el sistema Wally Trader siguiendo estos pasos exactos:

1. Si no estamos dentro del repo, clonalo con:
   git clone https://github.com/sasasamaes/wally-trader && cd wally-trader

2. Instalá la lib compartida + el MCP server:
   make wally-mcp-install

3. Activá el adapter Claude Code (symlinks system/ → .claude/):
   bash adapters/claude-code/install.sh

4. Verificá la instalación:
   make doctor

5. Reportame:
   - Qué checks pasaron y cuáles fallaron en doctor
   - El path del venv Python que se creó
   - Cualquier dependencia que falte (libomp para xgboost, etc.)

Después leé CLAUDE.md para entender el sistema y avisame que estás listo para trading.
```

### 🐧 OpenClaw

```
Install the Wally Trader system. Run these exact steps:

1. If not in the repo, clone:
   git clone https://github.com/sasasamaes/wally-trader && cd wally-trader

2. Install the shared library and MCP server:
   make wally-mcp-install

3. Activate the OpenClaw adapter (generates .openclaw/ skills + config):
   bash adapters/openclaw/install.sh

4. (Optional) If you want to use OpenRouter for multi-model access instead of Anthropic API:
   WALLY_USE_OPENROUTER=1 bash adapters/openclaw/install.sh
   And set OPENROUTER_API_KEY in your env.

5. Verify the install:
   make doctor

6. Report back:
   - All checks passed/failed
   - Whether .openclaw/skills/wally-{agents,commands}/ has the expected count (17 + 44)
   - Model provider in .openclaw/config.json (anthropic/* or openrouter/*)

Then read docs/openclaw-setup.md for the full operational guide.
```

### 💻 OpenCode

```
Instalá el sistema Wally Trader para OpenCode:

1. Cloná el repo si no lo tenés:
   git clone https://github.com/sasasamaes/wally-trader && cd wally-trader

2. Instalá la lib compartida + MCP propio:
   make wally-mcp-install

3. Activá el adapter OpenCode (genera .opencode/ y instala git pre-commit hook):
   bash adapters/opencode/install.sh

4. Verificá la instalación:
   make doctor

5. Mostrame:
   - Qué checks pasaron en doctor
   - Cantidad de comandos y agentes generados en .opencode/
   - Si necesito setear alguna API key

Después leé AGENTS.md (si existe) o CLAUDE.md.
```

### 🤝 Hermes (Telegram / Discord / Slack)

```
Install the Wally Trader system for Hermes (multi-channel agent runtime).
End goal: send /punk-hunt or /chart from Telegram and have it work, including
drawing on TradingView Desktop on this Mac.

Steps:

1. If not in the repo, clone:
   git clone https://github.com/sasasamaes/wally-trader && cd wally-trader

2. If Hermes is not installed yet:
   curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

3. Install the shared library + MCP server:
   make wally-mcp-install

4. Activate the Hermes adapter (regenerates .hermes/skills/ AND auto-registers
   tradingview + wally + notion MCP servers in Hermes config):
   make hermes-install

5. Verify with smoke test (6 checks):
   make hermes-smoke

6. Report:
   - 6/6 checks passing? Which failed?
   - Output of: hermes config get mcp.tradingview.command
   - Output of: hermes config get mcp.wally.command
   - Output of: hermes config get mcp.notion.command

After this, the user still needs to manually:
- Configure Telegram bot token (BotFather → hermes config set telegram.bot_token X)
- Set allowed_chat_ids
- Run: make hermes-daemon-install (to keep Hermes always-on via launchd)

Read docs/hermes-setup.md for the full Telegram/daemon setup guide.
```

### ⚡ Atajo bash (sin agente)

Si preferís terminal directa:

```bash
git clone https://github.com/sasasamaes/wally-trader && cd wally-trader \
  && make wally-mcp-install \
  && bash adapters/claude-code/install.sh \
  && bash adapters/openclaw/install.sh \
  && bash adapters/opencode/install.sh \
  && make hermes-install \
  && make doctor
```

Esto deja los 4 harnesses listos. Después podés usar el que prefieras según contexto.

### 🩺 Verificación post-instalación

| Comando | Qué verifica |
|---|---|
| `make doctor` | Health check general (Python deps, MCP servers, profiles, locks) |
| `make hermes-smoke` | 6 checks específicos de Hermes (CLI, skills, MCPs, venv) |
| `make test-unit` | 72 tests de lógica (regime, validate, risk, locking, memory) |
| `make test-integration` | 27 tests de las MCP tools |

Los 4 deben dar verde antes de operar capital real.

---

## 📁 Estructura del proyecto

```
trading/
├── CLAUDE.md                      # Guía del proyecto (Claude lee al iniciar)
├── MORNING_PROMPT.md              # Protocolo matutino retail (17 fases)
├── MEAN_REVERSION_INDICATOR.pine  # Indicador Pine Script (4 filtros + alertas)
├── DAILY_TRADING_JOURNAL.md       # Template journal diario
├── RISK_CALCULATOR.md             # Fórmulas de position sizing
├── README.md                      # Este archivo
│
├── system/                        # 📌 CANONICAL SOURCE OF TRUTH (multi-CLI)
│   ├── commands/                  # 33 slash commands markdown (formato CC)
│   ├── agents/                    # 12 agentes (incluye morning-analyst-ftmo)
│   ├── skills/                    # 21 skills custom (incluye Neptune + punkchainer playbook)
│   ├── mcp/servers.json           # MCP config neutral
│   ├── hooks/                     # placeholder para hooks compartidos
│   └── README.md                  # Flujo de sync + adapters
│
├── adapters/                      # Per-CLI translators
│   ├── claude-code/install.sh     # Symlinks .claude/ → system/
│   ├── opencode/                  # transform.py + pre-commit hook + watch
│   └── codex/                     # ⚠️ UNTESTED
│
├── .claude/                       # Claude Code harness
│   ├── settings.json              # statusline, hooks, permissions
│   ├── settings.local.json        # overrides locales (gitignored)
│   ├── .env                       # FTMO credentials (gitignored)
│   ├── .env.example               # template credenciales
│   ├── active_profile             # "retail | <iso>" o "ftmo | <iso>"
│   ├── commands/ → ../system/commands/   # symlink
│   ├── agents/   → ../system/agents/     # symlink
│   ├── skills/   → ../system/skills/     # symlink
│   ├── profiles/                  # 🆕 Profile-scoped config + memoria (7 profiles)
│   │   ├── retail/                # Binance main $18.09 (post-migración)
│   │   │   ├── config.md
│   │   │   ├── strategy.md
│   │   │   └── memory/            # + pending_orders.json (watcher v1)
│   │   ├── retail-bingx/          # BingX residual $0.93 (pedagógico)
│   │   │   ├── config.md
│   │   │   └── memory/            # + pending_orders.json
│   │   ├── ftmo/                  # $10k demo multi-asset
│   │   │   ├── config.md
│   │   │   ├── strategy.md
│   │   │   ├── rules.md
│   │   │   ├── memory/            # equity_curve, pending_orders, challenge
│   │   │   └── mt5_ea/            # ClaudeBridge.mq5 (EA bridge)
│   │   ├── fotmarkets/            # Bonus $30 MT5 (Mauritius, bonus-only)
│   │   │   ├── config.md
│   │   │   ├── strategy.md        # Fotmarkets-Micro (5m reversal)
│   │   │   ├── rules.md
│   │   │   └── memory/            # phase_progress + pending_orders + session_notes
│   │   ├── fundingpips/           # 🆕 $10k funded MT5 (real money desde día 1)
│   │   │   ├── config.md
│   │   │   ├── strategy.md        # FundingPips-Conservative (0.3% risk, 5% DD)
│   │   │   └── rules.md
│   │   ├── bitunix/               # 🆕 Copy-trading punkchainer's $50 (validar señales)
│   │   │   ├── config.md
│   │   │   ├── strategy.md        # 8-step pipeline + 4-pilar SMC + Saturday Protocol
│   │   │   ├── rules.md
│   │   │   └── memory/            # signals_received.md tracking
│   │   └── quantfury/             # 🆕 BTC-denominated 0.01 BTC (outperformance vs HODL)
│   │       ├── config.md
│   │       ├── strategy.md
│   │       ├── rules.md
│   │       └── memory/hodl_benchmark.md
│   └── scripts/
│       ├── profile.sh             # Switch profile activo
│       ├── guardian.py            # 🆕 Rules engine FTMO (3%/10%/Best Day)
│       ├── mt5_bridge.py          # 🆕 JSON parser/writer para EA bridge
│       ├── test_guardian.py       # 24 unit tests
│       ├── test_mt5_bridge.py     # 19 unit tests
│       ├── test_integration.sh    # 8 e2e tests
│       ├── backtest_ftmo.py       # Skeleton backtest FTMO-Conservative
│       ├── statusline.sh          # [RETAIL] o [FTMO $10k] + métricas
│       ├── session_start.sh       # Profile-aware context injection
│       ├── stop_hook.sh           # Auto-commit journal
│       ├── preprompt_check.sh     # Detecta auto-sabotaje
│       ├── notify.sh              # Notificaciones macOS
│       ├── daily_cron.sh          # Cron 5:30 AM
│       ├── pending_lib.py         # 🆕 CRUD + invalidation + whitelist matrix
│       ├── price_feeds.py         # 🆕 HTTP prices Binance/OKX/TwelveData
│       ├── notify_hub.py          # 🆕 Multi-channel notify (macOS + stubs TG/email)
│       ├── watcher_tick.py        # 🆕 Launchd target — orchestrator hourly
│       ├── watcher_escalate.sh    # 🆕 Dedupe spawn de `claude -p /watch-deep`
│       ├── order_lib.py           # 🆕 build_order + sizing_for_profile + whitelist
│       ├── binance_real_order.py  # 🆕 Stub v1 para --real flag
│       ├── NOTIFY_SETUP.md        # 🆕 Guía manual (launchd/FDA/Telegram/email)
│       └── tests/                 # 🆕 42 pytest tests (pending_lib + price + notify + tick)
│
├── .claude/watcher/               # 🆕 Watcher system
│   ├── whitelist_matrix.yaml      # Reglas cross-profile (editable)
│   ├── status.json                # Último tick (auto-generado)
│   ├── dashboard.md               # Estado legible (auto-generado cada tick)
│   ├── install_agent.sh           # Portable installer (resuelve paths runtime)
│   ├── uninstall_agent.sh         # Cleanup completo
│   ├── launchd/
│   │   └── com.wallytrader.watcher.plist.template  # Template con __APP_EXECUTABLE__
│   └── WallyWatcher.app/          # Bundle macOS (icono 🌭 + Info.plist)
│       └── Contents/
│           ├── Info.plist         # CFBundleDisplayName "Wally Trader Watcher"
│           ├── MacOS/WallyWatcher # Launcher script (config via ~/.config/wallytrader.conf)
│           └── Resources/wally.icns # Dachshund icon (multi-size)
│
├── .opencode/                     # 🆕 Generated by adapters/opencode (committed)
│   ├── commands/                  # 23 translated (CC → OC format)
│   ├── agents/                    # 12 translated
│   ├── skills/ → ../system/skills/ # symlink (format compatible)
│   └── config.json                # MCP servers.tradingview
│
├── scripts/ml_system/             # Capa ML (NLP + XGBoost + LSTM scaffold)
│   └── ...                        # ver sección ML más abajo
│
├── docs/superpowers/              # 🆕 Specs + plans + implementation logs
│   ├── specs/                     # Design docs aprobados
│   └── plans/                     # Implementation plans + logs
│
└── tradingview-mcp/               # MCP server TradingView (submodule externo)

├── scripts/ml_system/             # Capa ML (NLP + XGBoost + DL scaffold)
│   ├── README.md                  # Doc maestra del sistema ML
│   ├── setup.sh                   # Instalador de dependencias
│   ├── requirements.txt           # Deps Python (requests, vader, xgboost, ...)
│   ├── sentiment/                 # NLP Sentiment Aggregator (ACTIVO)
│   │   ├── aggregator.py          # Entrypoint /sentiment
│   │   └── sources.py             # F&G + Reddit + News RSS + Funding
│   ├── supervised/                # XGBoost LONG/SHORT (ACTIVO)
│   │   ├── data_loader.py         # Binance klines API (sin key)
│   │   ├── features.py            # 12 features técnicas
│   │   ├── train.py               # Entrena + calibra + guarda modelo
│   │   ├── predict.py             # Score 0-100 sobre setup actual
│   │   └── model/                 # Modelo .pkl + metrics.json (gitignored)
│   ├── deep/                      # LSTM scaffold (NO ACTIVO)
│   │   ├── README.md              # Precondiciones de activación
│   │   └── lstm_scaffold.py       # Arquitectura lista para activar
│   └── shared/config.py           # Paths y constantes

# Repos externos (no incluidos en este repo):
├── tradingview-mcp/               # MCP server de TradingView (submódulo externo)
└── claude-tradingview-mcp-trading/  # Bot adicional (submódulo externo)

# Memoria persistente (fuera del repo, en ~/.claude/):
~/.claude/projects/<project-path-encoded>/memory/
├── MEMORY.md                      # Índice de memorias
├── user_profile.md                # Perfil del trader
├── trading_strategy.md            # Config de estrategia activa
├── market_regime.md               # Cómo detectar régimen de mercado
├── trading_log.md                 # Historial de trades
├── morning_protocol.md            # Protocolo de 17 fases (versión memoria)
├── entry_rules.md                 # Filtros de entrada + lecciones
├── backtest_findings.md           # Resultados de backtests
├── tradingview_setup.md           # Setup de TV + workarounds
├── market_context_refs.md         # APIs públicas útiles
├── communication_prefs.md         # Preferencias de comunicación
└── user_goals_reality.md          # Expectativas vs realidad
```

---

## 🏆 Estrategia actual: Mean Reversion en Range

**Validada con 100% WR en primer trade** (2026-04-20, +$1.14 sobre $10 cap).

### Parámetros

| Parámetro | Valor |
|---|---|
| Timeframe | 15m |
| Donchian length | 15 velas |
| Bollinger Bands | (20, 2) |
| RSI | 14 (OB 65 / OS 35) |
| ATR | 14 |
| Stop Loss | 1.5 × ATR |
| TP1 (40%) | 2.5 × SL |
| TP2 (40%) | 4.0 × SL |
| TP3 (20%) | 6.0 × SL |
| Leverage | 10x |
| Position sizing | 2% risk del capital |
| Ventana entradas | CR 06:00 – 23:59 |
| Cierre forzado | CR 23:59 (no dormir con posición abierta) |
| Max trades/día | 3 |
| Stop sesión | 2 SLs → para |

### 4 filtros obligatorios (todos deben cumplirse)

**LONG:**
1. Precio toca o cruza Donchian Low (dentro 0.1%)
2. RSI(14) < 35
3. Low de vela toca Bollinger Band inferior
4. Vela cierra verde (close > open)

**SHORT:** mirror (Donchian High, RSI > 65, BB superior, vela roja)

### Estrategia secundaria (si regime cambia)

**Donchian Breakout** cuando close 4H rompe el rango macro (ahora 73,500-78,300) con volumen >2x promedio. Config documentada en `CLAUDE.md`.

---

## 🌅 Uso diario

El sistema opera en **7 profiles aislados**. Al iniciar el día eliges cuál operar — no mezclar profiles distintos el mismo día (regla cross-asset BTC: nunca BTC simultáneo en múltiples profiles).

### Profile switching (inicio de día)

```bash
cd ~/Documents/wally-trader
claude

# Dentro de Claude Code:
/profile               # ver profile activo + timestamp
/profile retail        # switch a retail (Binance $18.09 — main, capital propio)
/profile retail-bingx  # switch a retail-bingx (BingX $0.93 — residual)
/profile ftmo          # switch a FTMO ($10k demo, challenge 1-step)
/profile fotmarkets    # switch a fotmarkets (bonus $30 MT5, sin depósito)
/profile fundingpips   # switch a fundingpips ($10k funded directo, dinero real)
/profile bitunix       # 🆕 switch a bitunix (copy-validated punkchainer's $50)
/profile quantfury     # 🆕 switch a quantfury (BTC-denominated 0.01 BTC)
/profile status        # resumen de los 7 profiles
```

Statusline refleja el profile activo + equivalente en colones:
- `[RETAIL] 💰 $18.09 ≈₡8,241 (+$8.09) │ 📊 0/3 │ 🟢 VENT │ 🕐 CR 06:00 │ BTC.P`
- `[FTMO $10k] Equity: $10,000 ≈₡4.6M • Daily: $+0 (0.0%) • EA ✓ 3s • Pos: 0`
- `[FOTMARKETS] $33.84 ≈₡15,415 | Fase 1 (→$100) | 🟢 VENT CR 07:30 | 0/1 trades`
- `[FUNDINGPIPS $10k] $10000.00 ≈₡4.5M | DD 🟢+0.00% | Daily 0.00% | 🟢 VENT CR 09:57 | 0/2 trades`
- `[BITUNIX] $50.00 ≈₡22,750 | 0/3 signals | 🟢 24/7 | hit_rate_filtered: —`
- `[QUANTFURY] 0.01000 BTC ≈$830 ≈₡378K | Daily Δ: +0 sats | vs HODL: +0.00%`

### Comparación rápida de profiles

| Profile | Capital | Tipo | Risk/trade | Max DD | Max trades/día | Plataforma |
|---|---|---|---|---|---|---|
| `retail` | $18.09 | Real propio | 2% | sin cap externo | 5 | Binance Futures |
| `retail-bingx` | $0.93 | Real residual | 2% (cosmético) | — | 3 | BingX |
| `ftmo` | $10k | Demo challenge | **0.5%** | 10% trailing | 3 | MT5 (FTMO-Demo) |
| `fotmarkets` | $30→$100→$300+ | Bonus no-deposit | 10%/5%/2% (phase) | 12% | 1-3 (phase) | MT5 (Fotmarkets) |
| `fundingpips` | $10k | **Real funded** ($99) | **0.3%** | **5% from initial** | **2** | MT5 (FundingPips-Live) |
| `bitunix` 🆕 | $50 | Copy-validated | 2% | -30% pause | 3 | Bitunix (referral `punkchainer`) |
| `quantfury` 🆕 | 0.01 BTC | BTC-denominated | 2% del BTC | -10% BTC stack | 3 | Quantfury (broker app) |

### Comandos cuantitativos disponibles (33 total)

**Análisis matutino y validación:**
```
/morning           análisis matutino completo (17 fases) profile-aware
/regime            detectar régimen rápido (RANGE/TRENDING/VOLATILE)
/validate          validar entry actual (4 filtros)
/signal            validar señal externa de comunidad
/ta                análisis técnico avanzado (ICT + harmónicos + Elliott + Fib)
/sentiment         score sentiment 0-100 (F&G + Reddit + News + Funding)
/levels            niveles técnicos actuales (Donchian, BB, RSI, ATR)
/multifactor       ⭐ score 0-100 (Momentum + Vol + Trend + Volume)
/chainlink         ⭐ cross-check precio TV vs Chainlink Data Feeds
```

**Risk management y sizing:**
```
/risk              position sizing flat 2% (regla simple)
/risk-var          ⭐ VaR/CVaR adaptativo (auto-reduce en alta vol)
/risk-parity       ⭐ multi-asset weights inverse-vol (FTMO/fotmarkets)
/trail             trailing stop EMA(20) para runner TP3
```

**ML / quant:**
```
/ml                XGBoost score TP-first del setup actual
/ml-train          re-entrenar modelo (descarga 1yr Binance + fit)
/macross           señal MA Crossover (EMA 9/21) — strategy TRENDING
/backtest          backtest config sobre data histórica
```

**Watcher / pending orders:**
```
/order             encolar orden limit virtual
/pending           listar pending orders activas
/watch             tick manual del watcher
/watch-deep        validación profunda de pending vía MCP
/sync              sync con MT5 state (FTMO)
/filled            confirmar fill manual
```

**Journal / review:**
```
/journal           ⭐ cierra día con métricas (Sharpe, Max DD, IC)
/review            review semanal/mensual
/status            estado completo del sistema
/equity <valor>    actualizar equity FTMO manualmente
/challenge         dashboard FTMO progress
/trades            dashboard MT5 fotmarkets
```

**Bitunix copy-validated + autónomo (NUEVO 2026-05-04):**
```
/punk-morning      ⭐ ritual pre-sesión: scan exhaustivo 32 assets + Neptune setup TV
/punk-hunt         ⭐ caza autónoma cada ~1h: scoring 4 confluencias Elite Crypto +
                     Hyper Wave numérico + TPs adaptativos al contexto + time gate <60min
/punk-hunt --tier-0 🆕 caza solo subset MUGRE (9 meme/low-cap del canal mugre-signals)
                     con reglas estrictas: score≥80, leverage 3x, margin 15%, risk 1%, DUREX 1R
/punk-watch        ⭐ vigilancia adaptativa trade activo: recalcula context cada 30 min,
                     forecast catalysts próximas 4-12h, time-out 90 min, matriz combinada
                     elapsed×context para decidir CERRAR/AGUANTAR/AJUSTAR
/log-outcome       cierra outcome de signal bitunix (TP1/TP2/TP3/SL/manual)
```

**Helpers Bitunix:**
```bash
python3 .claude/scripts/bitunix_pairs_check.py --tier 0          # validar listings TIER 0
python3 .claude/scripts/bitunix_pairs_check.py --symbols DOGE,WIF # validar custom
```

**Misc:**
```
/profile           switch profile
/chart             redibujar niveles en TradingView
/alert             configurar alerta macOS
/neptune           leer outputs de indicadores Neptune
```

⭐ = nuevos en esta versión (Chainlink + QuantMuse + Bitunix adaptive trading suite).

---

### 🏠 Workflow RETAIL (BingX $13.63 — el sistema original)

### 1. Preparación nocturna (el día anterior)
- Review del día
- Actualizar `DAILY_TRADING_JOURNAL.md`
- Dormir 7+ horas

### 2. Mañana 5:30 AM CR
Abre Claude Code en este directorio:
```bash
cd ~/Documents/trading
claude

# Si el profile activo es ftmo, switch primero:
/profile retail
```

### 3. Invoca el agente matutino
Dile a Claude: **"análisis matutino"** o **"morning analysis"**, o usa `/morning`.

Con profile=retail, Claude despacha automáticamente el agente `morning-analyst` (retail-only, 17 fases BTC-BingX).

Alternativamente, copia el bloque `PROMPT PRINCIPAL` de `MORNING_PROMPT.md`.

Claude ejecuta 17 fases en ~5-8 minutos:
- Auto-check personal
- Sentiment global (F&G, funding, on-chain)
- Correlaciones (ETH, SPX, DXY)
- Noticias/eventos próximas 6h
- Detección de régimen (range/trend/volatile)
- Selección de estrategia
- Niveles técnicos multi-TF
- Money flow + patrones
- Position sizing con tu capital
- Dibujo en TradingView
- Plan de entrada exacto
- Checklist pre-entry
- Reglas duras
- **VEREDICTO:** ENTRAR LONG / ENTRAR SHORT / ESPERAR / NO OPERAR

### 4. Ejecución disciplinada
- Imprime el checklist pre-entry (sección en `MORNING_PROMPT.md`)
- Tacha cada ítem antes de apretar COMPRAR/VENDER
- Si no puedes tachar los 15 → **no entres**

### 5. Cierre de sesión CR 17:00
```
"Cierre sesión. Resumen PnL + actualiza trading_log.md"
```

### 6. Review semanal (domingos)
```
"Review semana: métricas, patrones, 1 cambio para la próxima"
```

---

### 🏦 Workflow FTMO ($10k demo — multi-asset)

> **Prerequisitos:** `.claude/.env` llenado con credenciales FTMO + `ClaudeBridge.mq5` EA instalado en MT5 (ver [Setup inicial](#-setup-inicial)).

### 1. Inicio de día FTMO

```bash
cd ~/Documents/trading
claude

/profile ftmo
/equity 10247        # actualizar equity si cambió desde ayer (lee tu MT5)
/challenge           # dashboard de progreso (profit acumulado, rules, DD)
```

### 2. Análisis matutino multi-asset

```
/morning
```

Claude despacha `morning-analyst-ftmo` (14 fases). Analiza 6 assets del universo (BTC, ETH, EURUSD, GBPUSD, NAS100, SPX500), detecta régimen por asset, invoca guardian pre-check, selecciona 1 setup A-grade del día.

### 3. Esperar zona + validar

```
/validate            # 7 filtros (vs 4 del retail) + guardian verdict
```

Si todos 7 ✓ y guardian OK, Claude ofrece auto-`/order`:

```
¿Ejecutar orden ahora? Responde YES para encolar al EA, AJUSTAR <param> <val>, o NO.
```

### 4. Encolar orden (YES typed obligatorio)

Claude escribe la orden a `pending_orders.json` + envía a `mt5_commands.json`. Si el EA está vivo (heartbeat < 60s), ejecuta en MT5 automático. Si EA offline → modo manual, tú copias los params a MT5.

### 5. Monitoreo durante el día

```
/trades              # dashboard: posiciones abiertas, pendientes, cerradas hoy, PnL diario
/sync                # fuerza refresh del state desde MT5
```

Guardian bloquea entradas nuevas si:
- Daily PnL llegará a ≤ -3% con SL → **BLOCK_HARD** o **BLOCK_SIZE** con reducción
- 2 SLs consecutivos hoy → **BLOCK_HARD**
- 2 trades ya ejecutados → **BLOCK_HARD** (cap diario)

### 6. Force exit 16:00 CR

FTMO no permite overnight (y el sistema lo refuerza). A las 16:00 CR cierra todo.

### 7. Cierre de día

```
/journal
```

Auto-ingesta `closed_today` del EA, actualiza `trading_log.md` de FTMO, llama a `guardian --action equity-update` con el nuevo equity, marca pending expired, resume métricas del día.

### 8. Validación antes de challenge pago

**Paper trading obligatorio** en FTMO Free Trial 14 días. Criterios para pagar challenge $93.43:
- WR ≥ 55% sobre 10+ trades paper
- 0 daily breaches simulados
- 0 overrides del guardian
- Max DD ≤ 5%

Detalles en `docs/superpowers/plans/2026-04-22-ftmo-profile-IMPLEMENTATION-LOG.md`.

---

### 🪙 Workflow BITUNIX (copy-validated + autónomo $200) — actualizado 2026-05-04

> **Filosofía CORE: ROTACIÓN ALTA — 1 trade/hora.** Capital $200, target 1 trade ejecutado cada ~1h durante ventana operativa CR 06:00-23:00 (~17h). El edge tiene 2 fuentes:
> - **Copy-validated** señales Discord punkchainer's vía `/signal` (filtrar las malas)
> - **Self-generated** vía `/punk-hunt` con scoring 4 confluencias Elite Crypto + Hyper Wave numérico

#### 0. Setup TV inicial (1 vez, requiere TV Premium 5 indicadores)
Cargar manualmente desde "Indicadores → Requiere invitación":
1. `Neptune® - Signals™` (Range Filter + Reversal Bands + Smooth Trail + Trade Builder)
2. `Neptune® - Smart Money Concepts™` (Áreas de Interés + FVG + OB + ICT integrado)
3. `Neptune® - Oscillator™` (Hyper Wave numérico + Money Flow direction)
4. `Pivots and Phases™` (fases del MIT + pivots azules)
5. `Neptune® - Money Flow Profile™` (POC/VAH/VAL volume institucional)
Save Layout como "Bitunix Punk Setup".

#### 1. Inicio de día Bitunix (CR 06:00)
```
/profile bitunix
# Statusline: [BITUNIX] $200.00 ≈₡102,000 | 0/10 signals | 0/2 slots | 🟢 24/7

/punk-morning
# Ritual pre-sesión: macro gate + scan exhaustivo 32 assets +
# verifica Neptune cargado + DUREX/Saturday rules + slots disponibles
```

#### 2. Caza autónoma cada ~1h
```
/punk-hunt
# o /punk-hunt quick (top-5 líquidos, ~30s)
# Output: TOP setup ≥70 con TPs adaptativos al contexto + time gate <60min
```

**TPs adaptativos al contexto** (NUEVO):
- Contexto débil (Asia + ranging + low vol) → TPs CORTOS, capturar lo que da
- Contexto fuerte (NY overlap + trending alineado + high vol + smart money alineado) → TPs AMPLIOS
- Calculado por `.claude/scripts/context_multiplier.py` — combina 5 factores ortogonales

**SL adaptativo por volatilidad**:
- Low vol (ETH ~0.4% ATR) → SL apretado 1.3×ATR
- High vol (memecoin ~3% ATR) → SL muy amplio 3×ATR (para no salirse por mecha falsa)

**Sizing adaptativo por score** (NUEVO):
- Score 80+ → margin $70 (35% capital, 1.47% risk)
- Score 70-79 → margin $60 (30% capital, 1.26% risk)
- Score <70 → NO ABRIR
- Hard cap 35% capital por trade (permite 2 concurrentes)

#### 2.5. Caza meme/low-cap con `/punk-hunt --tier-0` (NUEVO 2026-05-05)

Modo opt-in para escanear el subset MUGRE — 9 tokens del canal `mugre-signals` de la comunidad punkchainer's (BIO, PENDLE, RAVE, BSB, BASED, OPG, BROCCOLI, BANANA, POWR). Volatilidad extrema + liquidez frágil → reglas más estrictas:

| Regla | Standard | **TIER 0 MUGRE** |
|---|---|---|
| Min score | 70 | **80** |
| Max leverage | 10x | **3x** |
| Max margin | 30% capital ($60) | **15% capital ($30)** |
| Risk per trade | 2% ($4) | **1% ($2)** |
| DUREX trigger | 20% recorrido TP1 | **1R** |
| CSV `tier` field | `standard` | **`mugre`** |

```bash
/punk-hunt --tier-0                                # caza autónoma del subset
python3 .claude/scripts/bitunix_pairs_check.py --tier 0    # re-validar listings (mensual)
```

**No afecta `/signal` Discord** — señales externas siguen reglas standard. Si la comunidad envía señal de un símbolo MUGRE, decidís manualmente bajar leverage al verlo.

**Tracking diferenciado:** la columna `tier` en `signals_received.csv` permite calcular WR mugre vs standard por separado. Si MUGRE WR <40% en 20 trades → desactivar el flag.

#### 3. Vigilancia adaptativa con `/punk-watch` cada 30 min
```
/loop 30m /punk-watch  # auto-loop opcional
```

**Recalcula contexto + sugiere ajustes:**
- Context multiplier ahora vs entry (delta % por factor)
- TPs recalculados (si delta >15% → sugiere ajuste manual en Bitunix)
- Forecast catalysts próximas 4-12h (sesiones, funding, macro)
- Matriz combinada **time elapsed × context delta** → recomendación clara CERRAR/AGUANTAR/AJUSTAR

**Time-out 90 min sin TP1 hit** → cierre forzado o ajuste explícito (regla anti-overstay).

#### 4. Cuando aparece señal en Discord punkchainer's
Ej: `MSTRUSDT Short 20x entry 166.57 sl=170 tp=160`

```
/signal MSTRUSDT short 166.57 sl=170 tp=160 leverage=20
```

El agente `signal-validator` ejecuta el pipeline 8-step:
Ej: `MSTRUSDT Short 20x entry 166.57 sl=170 tp=160`

```
/signal MSTRUSDT short 166.57 sl=170 tp=160 leverage=20
```

El agente `signal-validator` ejecuta el pipeline 8-step:
1. **Parse + null-checks** (sin SL → REJECT)
2. **4 filtros técnicos** (RSI/Donchian/BB/cierre)
3. **Multi-Factor + ML** cross-validation
4. **Chainlink** delta vs entry señal (<1%)
5. **Régimen + sentiment** check
6. 🆕 **4-Pilar Neptune SMC checklist** (visual manual con OB/FVG + Sweep + CHoCH + SFP)
7. 🆕 **Saturday Precision Protocol** (si fecha == sábado/domingo, gates más estrictos)
8. **Veredicto final** con override leverage 20→10

#### 5. Si APPROVE → ejecutar manual en Bitunix
- Login Bitunix (referral `punkchainer`)
- Open SYMBOL-PERP, side LONG/SHORT, leverage **10x** (override)
- Size 2% del capital, **margin max 30-35%** ($60-70 sobre $200)
- SL adaptativo por volatility (calculado en setup)
- **DUREX rule:** mover SL a BE en 20% recorrido a TP1 (1R en weekend)

#### 6. Tracking obligatorio
Cada señal validada (PASS/FLAG/REJECT) → `signals_received.md` (auto-log):
```markdown
## 2026-05-04 22:00 — ETHUSDT.P SHORT 10x (origen: /punk-hunt self-generated)
**Score:** 73/100 (Hyper Wave 92.47 extremo + cross bajista)
**Decisión:** EJECUTAR margin $100 (excedió cap recomendado 30-35%)
**TPs adaptativos:** TP1 $2,375 / TP2 $2,370 / TP3 $2,360
**Resultado:** DUREX hit 45min, BE+spread (lección: TPs originales 2R/3R/5R demasiado ambiciosos)
**Aprendizaje:** scoring funcionó pero TPs deberían ser adaptativos al context multiplier 0.30 (BAJO)
```

Cierre con `/log-outcome ETHUSDT TP1|TP2|TP3|SL|manual EXIT --pnl USD`.

#### 7. Métricas clave (`/journal bitunix`)
- `hit_rate_filtered` — WR de señales aprobadas por tu sistema
- `hit_rate_all` — WR si copiaras blindly (control)
- Si `filtered > all` → tus filtros agregan valor. Si `<` → over-restricción.

Skills críticos: `@punkchainer-glossary` (DUREX/GORRAS), `@punkchainer-playbook` (4-pilar + Saturday Protocol), `@neptune-community-config` (configs indicadores).

---

### ₿ Workflow QUANTFURY (BTC-denominated 0.01 BTC)

> Filosofía: "Bitcoin is the unit. USD is the noise." Mide PnL en BTC absoluto y compara contra **HODL benchmark** — si HODL hubiera dado más BTC stack, tu trading no tiene edge.

#### 1. Inicio de día Quantfury
```
/profile quantfury
# Statusline: [QUANTFURY] 0.01000 BTC ≈$830 ≈₡378K | vs HODL: +0.00%
```

#### 2. Análisis régimen-aware
- **TRENDING UP** → prefer HODL > longs (replica spot)
- **TRENDING DOWN** → SHORTS direccionales (fase oro para acumular BTC)
- **RANGE** → Mean Reversion ambos lados (igual que retail)
- **VOLATILE** → NO operar

#### 3. Sizing en BTC absoluto
Con 0.01 BTC, risk 2% = 0.0002 BTC. Calcular qty con SL distance, leverage cap 5x effective.

#### 4. Outperformance check (semanal)
```bash
bash .claude/scripts/btc_outperform.py --period 30d
# Output: tu_PnL_BTC vs HODL_PnL_BTC = delta% (positivo = added value)
```

#### 5. Reglas duras
- Daily BTC PnL ≤ -2% → BLOCK día
- Total DD ≤ -10% del BTC stack → BLOCK profile
- **Outperformance vs HODL <-2% mensual → PAUSAR profile 30 días** (admite que no hay edge)

---

## 🔔 Watcher & Set-and-Forget Orders (v1)

Sistema autónomo para programar entries matutinos y que el sistema los vigile mientras trabajas en otras cosas. Funciona en los 4 profiles principales (`retail`, `retail-bingx`, `ftmo`, `fotmarkets`) — virtual-only en v1 (notifica cuando disparar, tú ejecutas manual).

### Workflow típico

**CR 06:00 — morning:**
```bash
/morning
# Claude propone: BTC LONG @ 77521, SL 77101, TP 78571, invalid 76900
/order BTCUSDT.P LONG 77521 sl=77101 tp=78571 ttl=6h invalid=76900
# → YES para confirmar → persiste en pending_orders.json
```

**Te vas a trabajar** (codear, meeting, gym).

**Durante el día (autónomo):**

| Tiempo | Comportamiento del watcher |
|---|---|
| Cada 1h (launchd) | `watcher_tick.py` lee pending, pulls precio Binance, evalúa invalidaciones |
| Precio >0.3% del entry | Heartbeat silencioso + actualiza `next_recheck_mx` en el JSON |
| Precio ≤0.3% del entry | Spawn `claude -p /watch-deep <id>` headless con MCP TV completo |
| `/watch-deep` | Valida 4 filtros (RSI, BB, Donchian, cierre vela). Si 4/4 → status `triggered_go` |
| Trigger GO | **🚨 macOS notif CRITICAL** + dibujo entry/SL/TPs en TV |
| TTL / precio rompe invalid / 2 SLs / force_exit | Auto-cancel + macOS notif WARN |

**Llega notif CRITICAL → ejecutas manualmente en Binance/MT5:**
```bash
/filled ord_20260424_104800_retail_btcusdtp_long
# Status → filled, append to trading_log, notify INFO
```

### Comandos clave

| Comando | Descripción |
|---|---|
| `/order <asset> <side> <entry> sl=X tp=Y ttl=Nh invalid=Z` | Encola orden virtual en el profile activo |
| `/pending` | Lista pendings del profile actual (`all` para cross-profile) |
| `/pending show <id>` | Detalle + status history |
| `/pending cancel <id>` | Marca `canceled_manual` (terminal) |
| `/pending modify <id> tp1=X` | Edit `tp1/tp2/tp3/ttl_hours/invalidation_price` |
| `/watch` | Fuerza un tick manual (no espera al launchd) |
| `/filled <id> [price=X]` | Confirma fill tras ejecutar manual en exchange/MT5 |
| `/status` | Incluye sección watcher con último tick + pending counts |

### Invalidaciones automáticas

El watcher auto-cancela cuando:
1. **TTL expired** — pasó `expires_at` sin tocar entry
2. **Precio rompe `invalidation_price`** — tesis muerta (ej: LONG 77521 con invalid 76900 → si close 4H <76900, cancela)
3. **2 SLs hoy en el profile** — regla STOP día hit, todas las pending del día mueren
4. **Force exit CR 23:59 (retail) / 16:00 (ftmo) / 10:55 (fotmarkets)** — no dormir con trade abierto

### Matriz whitelist cross-profile

Evita doble exposición direccional al mismo underlying entre profiles. Ejemplos:

| Escenario | Resultado |
|---|---|
| `retail BTCUSDT.P LONG` + `fotmarkets BTCUSD LONG` | ❌ La 2ª queda `suspended_policy` (mismo BTC, misma dirección) |
| `retail BTCUSDT.P LONG` + `fotmarkets EURUSD SHORT` | ✅ Ambas activas (assets distintos) |
| `retail BTCUSDT.P LONG` + `ftmo BTCUSD SHORT` | ⚠️ Hedge permitido con warning |
| `ftmo NAS100 LONG` + `fotmarkets NAS100 LONG` | ❌ 2 brokers MT5 = doble real-ish |

Reglas en `.claude/watcher/whitelist_matrix.yaml` (editable).

### Arquitectura técnica

```
USER: /order → pending_orders.json (profile-scoped)
                  │
                  ▼
          launchd (cada 1h)
                  │
                  ▼
         watcher_tick.py
            (stateless)
         ├─ load_all_pendings()
         ├─ apply_whitelist_matrix()
         ├─ price_for()        # HTTP Binance/OKX/TwelveData
         ├─ evaluate_invalidation()  # TTL/price/stopday/force_exit
         └─ distance check:
            ├─ >0.3% → heartbeat + next_recheck
            └─ ≤0.3% → spawn claude -p /watch-deep
                         │
                         ▼
                Claude headless (120s timeout)
                ├─ chart_set_symbol + MCP read
                ├─ Evalúa 4 filtros
                └─ notify_hub.notify()
                         │
                         ▼
              ┌──────────┴──────────┐
              ▼                     ▼
          macOS notif            dashboard.md + log
          (Glass/Submarine)      (auditoría)
```

### Instalación launchd (opcional — sistema funciona sin él vía `/watch` manual)

**Requisito:** brew python 3.12+ (evita el shim de Xcode en `/usr/bin/python3`).

```bash
# Si no tienes brew python:
brew install python@3.13

# Instalador portable — resuelve paths a runtime, funciona en cualquier Mac/usuario
bash .claude/watcher/install_agent.sh
```

El instalador:
1. Detecta repo desde su propia ubicación (puedes clonar en `~/code/`, `/opt/`, donde sea)
2. Busca Python 3.12+ disponible (prefiere 3.13)
3. Instala deps Python si faltan
4. Copia `.claude/watcher/WallyWatcher.app` a `~/.local/Applications/`
5. Escribe config runtime a `~/.config/wallytrader.conf` (REPO_ROOT + PYTHON)
6. Renderiza plist launchd con paths absolutos a `~/Library/LaunchAgents/`
7. Registra `.app` con LaunchServices (icono dachshund en Background Items)
8. `launchctl load`

```bash
# Verificar
launchctl list | grep wallytrader
launchctl start com.wallytrader.watcher
cat /tmp/wally_watcher.out
cat .claude/watcher/dashboard.md

# Desinstalar
bash .claude/watcher/uninstall_agent.sh
```

**macOS Full Disk Access:** `~/Documents` está protegido por TCC. Concede FDA al binario usado por launchd (`/opt/homebrew/bin/python3.13` o el que detectó el installer) en **System Settings → Privacy & Security → Full Disk Access**.

**Background Items:** tras instalar, *System Settings → General → Ítems de inicio y extensiones* muestra **"Wally Trader Watcher"** con icono 🌭 dachshund en vez de "bash".

### Rollback

```bash
bash .claude/watcher/uninstall_agent.sh
# Remueve plist + bundle + config. Sistema sigue funcional vía /watch manual.
```

### Stubs en v1 (activables después)

- `--real` flag en `/order` (para retail → Binance API real order): stub, imprime "not implemented"
- Telegram bot notifications: no-op silencioso si no hay `TELEGRAM_BOT_TOKEN` en `.claude/.env`
- Email via Resend: no-op silencioso si no hay `RESEND_API_KEY`

Docs completos para activar cada uno en `.claude/scripts/NOTIFY_SETUP.md`.

**Spec + plan:**
- `docs/superpowers/specs/2026-04-24-watcher-pending-orders-design.md`
- `docs/superpowers/plans/2026-04-24-watcher-pending-orders.md`

---

## 🤖 Capa ML (Sentiment + XGBoost + LSTM scaffold)

Sistema complementario en `scripts/ml_system/` que NO reemplaza las reglas mecánicas. Se usa como **5° filtro** cuando los 4 filtros técnicos ya están alineados.

### Componentes

| Componente | Estado | Qué hace |
|---|---|---|
| **NLP Sentiment** | ✅ Activo | F&G 35% + News VADER 30% + Reddit VADER 20% + Funding contrarian 15% → score 0-100 |
| **XGBoost Supervisado** | ✅ Activo | Predice probabilidad TP-first (LONG y SHORT) usando 12 features técnicas, calibrado con Platt |
| **LSTM Deep Learning** | ⏸️ Scaffold | No activo hasta cumplir precondiciones (capital ≥$500, n≥100 trades, etc.) |

### Setup inicial (primera vez)

```bash
cd scripts/ml_system
./setup.sh                              # instala requests, vader, xgboost, pandas, sklearn
brew install libomp                     # runtime para xgboost en Mac
python3 supervised/train.py --days 365  # entrena modelo (descarga ~100MB de Binance)
```

### Uso diario

```bash
# Sentiment (al iniciar sesión matutina)
python3 scripts/ml_system/sentiment/aggregator.py
# o slash command
/sentiment

# ML score sobre estado actual (cuando 4 filtros técnicos estén alineados)
python3 scripts/ml_system/supervised/predict.py --auto
# o slash command
/ml

# Re-entrenar (cada 2-4 semanas o si regime shift)
/ml-train
```

### Cómo interpretar scores

**Sentiment:**
| Score | Label | Acción |
|---|---|---|
| 0-19 | 🔴 EXTREME FEAR | Contrarian bullish — setups LONG tienen edge |
| 20-34 | 🟠 FEAR | Ligero bullish — cuidado con shorts |
| 35-69 | 🟡 NEUTRAL | Operar técnico puro, sin sesgo |
| 70-84 | 🟢 GREED | Ligero bearish — cuidado con longs tardíos |
| 85-100 | 🔴 EXTREME GREED | Contrarian bearish — setups SHORT tienen edge |

**ML Score (probabilidad TP-first):**
| Score | Acción |
|---|---|
| <35 | 🔴 BAJO — pasar o size 50% aunque técnico sea GO |
| 35-55 | 🟡 NEUTRAL — decisión por técnico puro |
| 55-70 | 🟢 FAVORABLE — modelo confirma el setup |
| >70 | 🟢 ALTO — edge histórico alto |

### Reality check honest-first

- AUC típico en crypto 15m: **0.52-0.62**. Más es sospechoso de overfitting.
- El modelo NO encuentra setups — solo confirma/cuestiona los que tu sistema técnico ya detectó.
- `/ml-train` corre automáticamente un reality check y warna si AUC >0.65 (posible leakage).
- Con n<20 trades reales, la varianza supera la señal. Trata el score ML como un voto más.

---

## 📋 Paso a paso diario (workflow óptimo)

Un día operativo completo usando TODO el stack (técnico + sentiment + ML). Ventana **CR 06:00 – 23:59** (cripto 24/7, pero no dormir con trade abierto).

### 🌅 CR 05:30 — Despertar

```bash
cd ~/Documents/trading
claude
```

El status line muestra: `💰 $13.63 (+$3.63) │ 📊 0/3 │ 🟢 VENT │ 🕐 CR 05:30 │ BTC.P`

### 🌄 CR 05:45-06:00 — Check personal

- [ ] Dormí 6+ horas
- [ ] Desayuné algo
- [ ] Estoy mentalmente claro (no tilt, no FOMO, no revenge)
- [ ] No estoy "recuperando" pérdida de ayer

Si alguno falla → **NO operar hoy**.

### ☀️ CR 06:00 — Análisis matutino (17 fases + ML)

```
/morning
```

El agente `morning-analyst` ejecuta el protocolo completo en 5-8 min. Al finalizar, complementa con:

```
/sentiment          # score NLP agregado para calibrar sesgo del día
/regime             # confirmación rápida de régimen (RANGE vs TRENDING vs VOLATILE)
/chart              # dibuja niveles actualizados en TradingView
```

**Veredicto posible:** `ENTRAR LONG` / `ENTRAR SHORT` / `ESPERAR` / `NO OPERAR`.

### 🎯 CR 06:00 – 23:30 — Monitoreo de setup

Durante la ventana, espera a que BTC toque una zona operativa (Donchian High/Low ±0.1%). Puedes dejar alerta activa:

```
/alert 4 filtros
```

**Cuando el setup 4/4 aparezca (validación completa):**

```
/validate           # 4 filtros técnicos (GO/NO-GO)
/ml                 # ML XGBoost: probabilidad TP-first
/multifactor        # ⭐ Multi-Factor score 0-100 (cross-validation con ML)
/chainlink          # ⭐ cross-check precio TV vs Chainlink (detecta wicks fake)
/risk-var           # ⭐ position sizing VaR/CVaR adaptativo (mejor que flat 2%)
/sentiment          # contrarian al extremo (F&G + Reddit + News + Funding)
```

**Decisión matriz extendida (6 capas de validación):**

| Técnico 4/4 | ML | Multi-Factor | Chainlink | Sentiment | Acción |
|---|---|---|---|---|---|
| ✅ GO | >60 | >70 | OK | Alineado | **MAX conviction** — full size con `/risk-var` |
| ✅ GO | >60 | 50-70 | OK | Neutral | **ENTRAR** con size 75% |
| ✅ GO | 40-60 | 40-60 | OK | Cualquiera | **ENTRAR** con size 50% |
| ✅ GO | >60 | <30 | OK | — | **DIVERGEN** — flag, reducir size 50% o skip |
| ✅ GO | <40 | <30 | OK | — | **PASAR** — esperar mejor setup |
| ✅ GO | cualquiera | cualquiera | **WARN** (delta 0.3-1%) | — | **CAUTION** — entrar con size 50%, validar feed |
| ✅ GO | cualquiera | cualquiera | **ALERT** (delta >1%) | — | **NO OPERAR** — feed stale o manipulación |
| ✅ GO | — | — | OK | Extremo contrario (LONG + F&G 90) | **PASAR** — sentiment contrarian wins |
| ❌ 3/4 o menos | — | — | — | — | **NO ENTRAR** — nunca forzar |

### 💥 Al entrar — Disciplina mecánica

1. Loggear **ANTES** de pulsar "Abrir" en BingX:
   - Hora CR exacta
   - Precio de entry
   - Los 4 filtros con checkmark uno por uno
   - SL planeado ($)
   - TP1/TP2/TP3 planeados ($)
   - Size calculado (en USDT)
   - Score ML y Sentiment del momento

2. Abrir posición:
   - SL colocado inmediatamente (nunca "después")
   - TPs escalonados: 40% TP1, 40% TP2, 20% TP3
   - TP1 hit → SL a breakeven automático

3. **NO TOCAR** una vez abierto. La posición ejecuta sola.

### ⏳ Durante el trade — Paciencia activa

- **NUNCA mover SL en contra.** Es la regla más violada y más cara.
- Si el precio se aleja del SL sin llegar a TP1 → puede pasar. Respira.
- Si necesitas cerrar manual (hora CR 23:30, evento macro imprevisto, pendiente personal) → cerrar a mercado sin mover SL.

### 🌙 CR 23:30 — Alarma de cierre próximo

Si el trade sigue abierto a las 23:30 CR:
- Evalúa si hay chance real de tocar TP antes de 23:59
- Si no → cerrar a mercado

### 🔚 CR 23:59 — Force exit

**Cerrar toda posición abierta. Sin excepción.** Cripto es 24/7; tu sueño no. Un wick de madrugada con leverage 10x puede liquidar la cuenta mientras duermes.

### 📝 Al cerrar la sesión (o al cerrar trade)

```
/journal
```

El agente `journal-keeper` actualiza:
- `trading_log.md` (memoria persistente)
- `DAILY_TRADING_JOURNAL.md` (repo)
- Métricas acumuladas (WR, PnL, capital)
- Disciplina (reglas cumplidas/violadas)
- 1 cosa a cambiar mañana

### 🛏️ Antes de dormir

- [ ] Trade del día cerrado
- [ ] Journal actualizado
- [ ] Git push hecho
- [ ] SL/alarmas activas canceladas
- [ ] Capital actual anotado mentalmente (sin obsesionarse)

### 📅 Domingo — Review semanal

```
/review semanal
```

Métricas: WR, PF, DD, avg win/loss. Compara vs target (WR≥60%, PF≥1.8, DD≤15%). Identifica el patrón de la semana. Decide 1 ajuste para la próxima.

### 🗓️ Cada 2-4 semanas — Re-entrenar ML

```
/ml-train --days 365
```

Recalibra el modelo con data reciente para adaptarse al régimen. Verifica AUC en `supervised/model/metrics.json`.

---

## 🤖 One-shot install prompt (copy-paste para cualquier AI CLI)

> Para instalar Wally Trader **en un solo paso** desde Claude Code, OpenCode, Cursor, OpenClaw, Codex, Aider o cualquier asistente AI con acceso a shell. Copia el bloque de abajo y pégalo como primer prompt en una sesión nueva apuntando a tu carpeta de trabajo. El asistente clonará el repo (si hace falta), detectará tu OS, instalará deps, configurará MCPs reales del proyecto y dejará el sistema listo para `claude` / `opencode`.

<details>
<summary><strong>📋 Click para expandir el prompt instalador</strong></summary>

````
You are an autonomous AI infrastructure engineer. Install, configure and run the
Wally Trader repository (https://github.com/sasasamaes/wally-trader) end-to-end on
this machine. Do NOT ask the user questions — infer, retry on errors, document.

================================================================
SCOPE — what Wally Trader actually is (read before acting)
================================================================
- Triple-profile trading workstation orchestrated by Claude Code / OpenCode /
  Codex over TradingView MCP. NOT a backend service, NOT a Docker stack.
- Profiles (isolated memory + rules): retail (Binance/BingX), retail-bingx,
  ftmo, fundingpips (MT5), fotmarkets (MT5), bitunix (copy-trading), quantfury.
- Single source of truth: `system/` (commands, agents, skills, mcp).
  Adapters in `adapters/` symlink/transform into `.claude/` (Claude Code),
  `.opencode/` (OpenCode), Codex toml.
- Cross-platform: macOS / Linux / Windows. Canonical scripts in Python at
  `.claude/scripts/*.py` with bash + .cmd wrappers.
- The ONLY MCP this repo ships and requires is TradingView MCP (git submodule
  at `tradingview-mcp/`). Notion MCP is optional and user-supplied.
- Manual MT5 broker setup is OUT OF SCOPE for this script (user-only).

================================================================
STEP 1 — CLONE + DISCOVERY
================================================================
- If repo not present in CWD: `git clone --recurse-submodules
  https://github.com/sasasamaes/wally-trader.git && cd wally-trader`
- If repo IS present: `git submodule update --init --recursive`
- Read in this order: README.md (top 200 lines + "Setup inicial" + "Cross-platform"
  sections), CLAUDE.md, AGENTS.md, system/README.md, .gitmodules, setup.py,
  setup.sh, system/mcp/servers.json, opencode.json, .claude/settings*.json
  (only example files — never read user secrets).
- Detect OS (uname / $OS), CLI present (`which claude`, `which opencode`,
  `which codex`), Python version, Node version.

================================================================
STEP 2 — CORE TOOLING (install only what is missing)
================================================================
Required:
  - git, python3.9+, pip, node.js LTS (>=18), npm
Recommended:
  - jq, curl, direnv
Per OS:
  - macOS: `brew install` for any missing piece. If brew absent, install brew first.
  - Linux (Debian/Ubuntu): `sudo apt update && sudo apt install -y …`
  - Windows: prefer Git Bash; assume user already has Python + Git for Windows;
    if not, document the exact winget/python.org install steps and STOP this step.

DO NOT install Docker — this repo does not use Docker.

================================================================
STEP 3 — REPO INSTALLER (use the project's own one-shot)
================================================================
Run the canonical installer (it auto-detects OS, installs Python deps,
generates OpenCode/Hermes adapters, and runs smoke tests):

  bash setup.sh         # macOS / Linux / Git Bash
  python setup.py       # any OS (works on native Windows too)
  .claude\scripts\win\setup.cmd     # Windows native cmd

If pip dep resolution fails: retry with `--quick` (skips plyer/vader).
If a single Python dep fails: install it manually with pip and re-run setup.

================================================================
STEP 4 — TRADINGVIEW MCP (the only mandatory MCP)
================================================================
- Submodule lives at `tradingview-mcp/`. After clone with --recurse-submodules
  it is already present.
- Install its Node deps: `cd tradingview-mcp && npm install && cd ..`
- The MCP entry is wired automatically:
  - Claude Code reads `.mcp.json` (already committed at repo root, points to
    `./tradingview-mcp/src/server.js`).
  - OpenCode reads `opencode.json`.
- TradingView Desktop must be launched by the USER with remote debugging on
  port 9222 BEFORE starting an analysis session. Document the launch command
  for their OS in TROUBLESHOOTING.md (see step 9). Do NOT attempt to launch it.

================================================================
STEP 5 — OPTIONAL MCPs (only if the user already has credentials)
================================================================
Check for env vars / existing config before configuring any of these.
If credentials are missing, SKIP and add a note to FULL_SETUP.md.

  - Notion MCP   → only if `NOTION_API_KEY` exists in env or `.env`.
                   Reference: docs/NOTION_SETUP.md inside the repo.
  - GitHub MCP   → only if `GITHUB_TOKEN` exists. Useful for `/review`.
  - Filesystem / Memory / Sequential-Thinking / Fetch MCPs from
    https://github.com/modelcontextprotocol/servers — install ONLY if user
    already has them globally; do NOT add them to this repo's mcp config
    unless asked. They are not part of the Wally Trader contract.

DO NOT invent SQLite/Postgres/Redis MCPs — Wally Trader is file-based
(JSON/CSV/MD under `.claude/profiles/<profile>/memory/`). No DB exists.

================================================================
STEP 6 — ENV FILE
================================================================
Create `.env` at repo root if missing, with these placeholders + comments
(never overwrite an existing .env, never commit it — `.gitignore` already
excludes it):

  # Required only for ML / sentiment features:
  # ANTHROPIC_API_KEY=
  # Optional integrations:
  # NOTION_API_KEY=
  # NOTION_DATABASE_ID=
  # GITHUB_TOKEN=
  # Trading broker bridges (MT5 EA reads these from MT5 itself, NOT from .env)

================================================================
STEP 7 — SMOKE TESTS
================================================================
Run, in order, and report pass/fail for each:
  python .claude/scripts/profile.py get
  python .claude/scripts/fx_rate.py
  python .claude/scripts/notify.py "Wally" "Install OK"
  python -m pytest tests/ -q     # 84 tests expected to pass
  node tradingview-mcp/src/server.js --help     # MCP boots

If any pytest test fails: print the failing test name, the first 30 lines of
its traceback, and continue. Do not abort the install over test failures.

================================================================
STEP 8 — PROFILE SELECTION (interactive ONE-LINER, optional)
================================================================
After setup, suggest the user pick a profile by running:
  python .claude/scripts/profile.py set retail
  # or: ftmo | fundingpips | fotmarkets | bitunix | quantfury | retail-bingx
This is the only manual decision required.

================================================================
STEP 9 — DOCUMENTATION DELTAS
================================================================
Generate ONLY if missing (do not overwrite existing docs):
  - INSTALL_REPORT.md  → what was installed, OS detected, versions, MCPs wired,
                          TVDesktop launch command for this OS, next steps.
  - TROUBLESHOOTING.md → only append your findings; do not duplicate the
                          existing Troubleshooting section in README.md.

================================================================
STEP 10 — FINAL OUTPUT
================================================================
Print exactly:
  1. OS detected
  2. Runtimes: python X.Y, node X.Y
  3. CLIs detected: claude / opencode / codex (yes/no each)
  4. MCPs configured: tradingview (mandatory), notion/github (if creds)
  5. Tests: <passed>/<total>
  6. Profile active: <name> (or "none — run profile.py set <name>")
  7. Launch command for this OS:
       macOS:   `claude` (or `opencode`)
       Linux:   `claude` (or `opencode`)
       Windows: `opencode` (recommended) or `claude` if installed
  8. Manual steps remaining (TradingView Desktop launch with port 9222,
     MT5 broker login if profile is ftmo/fundingpips/fotmarkets, etc.)

================================================================
RULES
================================================================
- NEVER commit secrets. NEVER push. NEVER `git add .env`.
- NEVER fabricate Docker/Postgres/Redis where none exists.
- NEVER overwrite the user's existing `.claude/profiles/<profile>/memory/`.
- Prefer the repo's own `setup.py` over reinventing install logic.
- On any error: try once more with verbose output, then document and continue.
- Stay in the repo working directory — do not modify $HOME beyond the
  symlinks `setup.py` itself creates.
````

</details>

**Resultado esperado:** sistema instalado, tests pasando (84/84), TradingView MCP wired, profile activo elegido por el usuario. Lo único que el asistente NO hace es lanzar TradingView Desktop con el puerto de debug (paso manual del usuario) ni loguearte en MT5/exchange (manual).

---

## 🔧 Setup inicial

### Requisitos

**Core (todos los profiles):**
- **Claude Code** (Anthropic CLI) — primario, mejor soporte (statusline, hooks, watcher)
- **TradingView Desktop** (plan Basic mínimo) + MCP conectado vía `--remote-debugging-port=9222`
- **Python 3.9+** con PyYAML (`pip3 install pyyaml` o `pip install pyyaml` en Windows)
- **Zona horaria:** sistema corre en CR (UTC-6, sin DST). Trabaja también para MX/CDMX (mismo offset).

## 🌐 Cross-platform support (macOS / Linux / Windows × Claude Code / OpenCode)

> **Sistema 100% cross-platform desde 2026-04-30**. Scripts canónicos en Python (`.claude/scripts/*.py`), bash wrappers (macOS/Linux), `.cmd`/`.ps1` wrappers (Windows). Todos delegan al mismo Python.

### Setup unificado (1 comando)

```bash
# macOS / Linux / Windows-Git-Bash:
bash setup.sh                # interactive
bash setup.sh --check        # solo verifica, no instala
bash setup.sh --quick        # skip optional deps (plyer, vader)

# Windows nativo (cmd.exe / PowerShell):
.claude\scripts\win\setup.cmd
.claude\scripts\win\setup.cmd --check

# O directo con Python (works everywhere):
python setup.py
python setup.py --check
```

`setup.py` autodetecta OS y:
1. Verifica Python 3.9+
2. Verifica deps de sistema (git, opcionales según OS)
3. Instala Python deps via pip (pyyaml, pandas, numpy, yfinance, xgboost, requests, plyer)
4. Genera adapters (OpenCode + Hermes)
5. Smoke test scripts canónicos
6. Reporta next steps específicos del OS

### Matriz de compatibilidad

| Feature | macOS | Linux | Windows + Git Bash | Windows nativo |
|---|---|---|---|---|
| **Slash commands core** (`/profile`, `/risk`, `/regime`...) | ✅ | ✅ | ✅ | ⚠️ Git Bash needed |
| **profile, fotmarkets_phase, fx_rate, chainlink, notify** | ✅ Python canónico | ✅ idem | ✅ idem | ✅ vía `.cmd`/`.ps1` |
| **Notificaciones desktop** | ✅ osascript | ✅ notify-send | ✅ via Git Bash | ✅ plyer/PowerShell |
| **TradingView MCP** | ✅ | ✅ | ✅ | ✅ |
| **Claude Code CLI** | ✅ recomendado | ✅ | ✅ | ✅ |
| **OpenCode CLI** | ✅ | ✅ | ✅ recomendado | ✅ recomendado |
| **Hermes Agent CLI** | ✅ | ✅ | ✅ via Git Bash | ⚠️ |
| **MT5 EA bridge** (FTMO/FundingPips/fotmarkets) | ✅ MT5 for Mac | ⚠️ Wine MT5 | ✅ nativo Windows MT5 | ✅ nativo |
| **Watcher daemon** | ✅ launchd `.app` | ⚠️ systemd manual | ⚠️ Task Scheduler manual | ⚠️ Task Scheduler manual |
| **Hooks** (SessionStart/Stop/PrePrompt) | ✅ Claude Code | ✅ Claude Code | ✅ Claude Code | ⚠️ OpenCode hook config |
| **Statusline** | ✅ macOS optimal | ✅ | ⚠️ formato puede variar | ⚠️ usar OpenCode UI |

### Arquitectura cross-platform (single source of truth)

```
.claude/scripts/
├── profile.py              ← Canonical Python (works everywhere)
├── profile.sh              ← bash wrapper → delegates to profile.py
├── fotmarkets_phase.py     ← Canonical
├── fotmarkets_phase.sh     ← bash wrapper
├── fx_rate.py              ← Canonical (USD↔CRC)
├── fx_rate.sh              ← bash wrapper
├── chainlink_price.py      ← Canonical (4 RPC fallbacks)
├── chainlink_price.sh      ← bash wrapper
├── notify.py               ← Canonical (macOS/Linux/Windows backends)
├── notify.sh               ← bash wrapper
└── win/                    ← Native Windows wrappers
    ├── _run_python.cmd     ← Helper: finds Python and execs
    ├── profile.cmd         ← Direct Windows usage
    ├── profile.ps1         ← PowerShell version
    ├── fotmarkets_phase.cmd
    ├── fx_rate.cmd
    ├── chainlink_price.cmd
    ├── notify.cmd
    └── setup.cmd           ← Setup launcher
```

**Single source of truth**: solo `*.py` tiene lógica. Wrappers son thin shims que:
1. Buscan Python (`python3` en macOS/Linux, `python` en Windows, fallback)
2. Ejecutan el `.py` con args forwarded
3. Propagan exit code

Esto significa: **fix un bug en `profile.py` y se arregla en macOS/Linux/Windows simultáneo**.

### Por OS — instalación específica

#### macOS

```bash
# 1. Python (si no instalado)
brew install python3

# 2. Setup
git clone https://github.com/sasasamaes/wally-trader.git
cd wally-trader
bash setup.sh

# 3. Lanzar
claude    # Claude Code (recomendado)
# o
opencode  # OpenCode
```

#### Linux (Ubuntu/Debian)

```bash
# 1. Python + libs sistema
sudo apt update && sudo apt install -y python3 python3-pip git libnotify-bin

# 2. Setup
git clone https://github.com/sasasamaes/wally-trader.git
cd wally-trader
bash setup.sh

# 3. Lanzar
claude
# o
opencode
```

Notificaciones desktop usan `notify-send` (paquete `libnotify-bin`). Si falta, las
notificaciones cae a stderr (no bloquea funcionalidad).

#### Windows 11

**Prereqs (orden de instalación):**

1. **Python 3.9+** desde [python.org](https://python.org) o Microsoft Store
   - ⚠️ **CRÍTICO**: marcar "Add Python to PATH" durante install
2. **Git for Windows** desde [git-scm.com/download/win](https://git-scm.com/download/win)
   - Incluye **Git Bash** + utilidades POSIX (bash, awk, sed, cut, curl, jq)
   - Esencial para slash commands con `bash .claude/scripts/...`
3. **OpenCode** (recomendado en Windows): `npm install -g opencode-ai`
4. **TradingView Desktop** Windows + MCP

**Setup:**

```powershell
# Clone
git clone https://github.com/sasasamaes/wally-trader.git
cd wally-trader

# Setup (cualquiera de estos funciona)
python setup.py                              # directo
.claude\scripts\win\setup.cmd                # cmd wrapper
bash setup.sh                                # Git Bash

# Smoke tests
python .claude\scripts\profile.py get
.claude\scripts\win\fx_rate.cmd
.claude\scripts\win\notify.cmd "Wally" "Hola Windows"

# Lanzar
opencode    # recomendado en Windows
# o
claude      # Claude Code (si tienes acceso)
```

**Si bash falla en Windows**: usa los `.cmd` directamente.
- En vez de `bash .claude/scripts/profile.sh get` → `.claude\scripts\win\profile.cmd get`
- Los slash commands en OpenCode pueden invocar el comando `python .claude/scripts/profile.py get` directamente (cross-platform).

### Notificaciones cross-platform

```python
# notify.py funciona idéntico en los 3 OS:
python .claude/scripts/notify.py "Title" "Message"

# Backend automático:
#   macOS:   osascript (built-in)
#   Linux:   notify-send (libnotify, fallback stderr si falta)
#   Windows: plyer (pip) → BurntToast PS → System.Windows.Forms ballontip → fallback stderr
```

Para instalar plyer en Windows: `pip install plyer` (incluido en `setup.py` opcional).

### Limitaciones por OS

| Limitación | macOS | Linux | Windows |
|---|---|---|---|
| Watcher daemon (`.app` bundle) | ✅ launchd | ❌ manual cron/systemd | ❌ Task Scheduler manual |
| Daily cron 5:30 AM | ✅ launchd | ⚠️ cron manual | ⚠️ Task Scheduler manual |
| MT5 native | ⚠️ macOS app sub-óptima | ❌ Wine | ✅ **nativo (recomendado)** |
| Claude Code statusline | ✅ optimal | ✅ | ⚠️ usar Windows Terminal con UTF-8 |
| Brew-only deps (`libomp` para XGBoost) | ✅ | N/A apt | ⚠️ pip directo |

**TL;DR profiles vs OS:**
- Si tu profile principal es **retail/quantfury (BTC trading)**: cualquier OS funciona ✅
- Si tu profile es **FTMO/FundingPips/fotmarkets (MT5)**: **Windows recomendado** (MT5 nativo)
- Si tu profile es **bitunix (copy-trading)**: cualquier OS, Windows un poco mejor por MT5

---

**Retail profile (Binance — main, default):**
- **Binance Futures** con BTCUSDT.P activado
- Capital real actual: **$18.09** (post-migración 2026-04-23)

**Retail-bingx profile (residual, pedagógico):**
- **BingX Futures** con BTCUSDT.P activado
- Capital actual: $0.93 (residual histórico)

**FTMO profile (opcional, para challenge):**
- **Cuenta FTMO Demo** (gratis 14 días Free Trial) o challenge $93.43
- **MT5 Desktop for Mac** instalado y loggeado al menos una vez
- Credenciales FTMO (login, password, server FTMO-Demo)

**Fotmarkets profile (bonus $30):**
- Bonus no-deposit Fotmarkets (Mauritius, MT5 Standard 1:500)
- Sin requerir depósito propio
- Multi-asset desbloqueado por fase (8 assets: forex/oro/indices/cripto)

**FundingPips profile (Zero $10k — direct funded, opcional):**
- Cuenta fondeada **real** desde día 1 ($99 una vez con código `HELLO -20%` = $79.20)
- **NO es challenge** — compras y operas directo
- MT5 con server `FundingPips-Live` (reusa EA bridge del FTMO)
- Multi-asset 20+ universe (forex/indices/crypto/oro)
- Reglas: 5% max DD, 3% daily, 15% consistency, 7 días min, leverage 1:50
- Payout bi-weekly 95% al trader

**Multi-CLI (opcional, hedge):**
- **OpenCode** — `curl -fsSL https://opencode.ai/install | bash` (free, soporte total v2)
- **Hermes Agent** (NousResearch) — `curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash` (free, soporte total v1, requiere cuenta API LLM como OpenRouter)
- **Codex** — OpenAI API key + `npm install -g @openai/codex` (adapter UNTESTED)

**Datos opcionales (gratis, sin auth):**
- **Chainlink price feeds** — usados por `chainlink_price.sh` vía RPC público (no requiere setup)
- **USD↔CRC FX rate** — `fx_rate.sh` usa `open.er-api.com` (no requiere setup)

### Usar este proyecto en OpenCode (soporte total)

El proyecto tiene **soporte completo** para OpenCode (https://opencode.ai/docs/es) además de Claude Code. La fuente de verdad es `system/` (commands, agents, skills, mcp); `adapters/opencode/` traduce automáticamente a `.opencode/` + `opencode.json` raíz.

**Primer uso:**
```bash
# 1. Genera .opencode/ + opencode.json (idempotente, cero side effects)
bash adapters/opencode/install.sh

# 2. Verifica
python3 -m pytest adapters/opencode/test_transform.py -v   # 15 tests

# 3. Lanza OpenCode dentro del repo
cd /Users/josecampos/Documents/wally-trader
opencode
```

**Qué obtienes:**
- `opencode.json` raíz con `model`, `instructions: [CLAUDE.md, AGENTS.md]`, `permission`, `mcp.tradingview`, `watcher.ignore`
- `AGENTS.md` raíz — leído por OpenCode automáticamente al iniciar sesión
- `.opencode/agents/` — 12 subagents (`@morning-analyst`, `@regime-detector`, etc.) auto-traducidos
- `.opencode/commands/` — 29 slash commands (`/morning`, `/profile`, `/risk`, etc.)
- `.opencode/skills/` — symlink a `system/skills/` (21 skills técnicas + Neptune + punkchainer playbook)
- `.opencode/config.json` — back-compat (legacy MCP block)

**Auto-sync:** un git pre-commit hook (instalado por `install.sh`) regenera `.opencode/` + `opencode.json` cada vez que tocas `system/commands/`, `system/agents/`, o `system/mcp/`. No tienes que ejecutar el adapter manualmente.

**Watcher mode (opcional, durante dev):**
```bash
brew install fswatch
bash adapters/opencode/watch.sh   # daemon que regenera al editar system/
```

**Diferencias OpenCode ↔ Claude Code:**
| Feature | Claude Code | OpenCode |
|---|---|---|
| Config primary | `.claude/settings.json` | `opencode.json` (raíz) |
| Instrucciones | `CLAUDE.md` | `AGENTS.md` + `CLAUDE.md` (vía `instructions`) |
| Subagents | `.claude/agents/*.md` | `.opencode/agents/*.md` |
| Slash commands | `.claude/commands/*.md` | `.opencode/commands/*.md` |
| Hooks (SessionStart, Stop, …) | ✅ nativos | ❌ no soportados — ejecutar manualmente si necesitas |
| Statusline | ✅ `statusLine.command` | ❌ usa el TUI default; `statusline.sh` aún funciona si lo invocas a mano |
| MCP | `~/.claude.json` (user-scope) o `.mcp.json` | `mcp` block en `opencode.json` |
| Plan mode | ❌ | ✅ Tab toggle |

**Limitaciones conocidas (vs Claude Code):**
- Los hooks `session_start.sh` / `stop_hook.sh` / `preprompt_check.sh` **no se ejecutan automáticamente** en OpenCode. Si necesitas el contexto del SessionStart, córrelo manualmente: `bash .claude/scripts/session_start.sh`.
- El statusline con USD↔CRC vive en `.claude/scripts/statusline.sh` y solo lo lee Claude Code. En OpenCode lo puedes inspeccionar manualmente con: `bash .claude/scripts/statusline.sh`.

### Usar este proyecto en Hermes Agent (soporte total)

El proyecto tiene **soporte completo** para [Hermes Agent (NousResearch)](https://github.com/NousResearch/hermes-agent) — el agente con loop de aprendizaje integrado, cron scheduling nativo, y delivery a Telegram/Discord/Slack/WhatsApp. La fuente de verdad sigue siendo `system/`; `adapters/hermes/` traduce a skills nativos del estándar [agentskills.io](https://agentskills.io).

**Primer uso (sin tener Hermes instalado):**
```bash
# 1. Genera .hermes/skills/ desde system/ (idempotente, sin requerir Hermes)
bash adapters/hermes/install.sh

# 2. Verifica
python3 -m pytest adapters/hermes/test_transform.py -v   # 12 tests
```

**Cuando instales Hermes:**
```bash
# 3. Install Hermes
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

# 4. Re-run install.sh — esta vez crea symlink ~/.hermes/skills/wally-trader/ → <repo>/.hermes/skills/
bash adapters/hermes/install.sh

# 5. Setup Hermes (model + provider)
hermes setup

# 6. Configura TradingView MCP (opcional)
hermes config set mcp.tradingview.command node
hermes config set mcp.tradingview.args '["./tradingview-mcp/src/server.js"]'

# 7. Lanza Hermes — auto-loads AGENTS.md + 66 skills (12 agents + 33 commands + 21 skills)
cd /Users/josecampos/Documents/wally-trader
hermes
```

**Qué obtienes:**
- `.hermes/skills/wally-agents/` — 12 skills traducidos desde `system/agents/`
- `.hermes/skills/wally-commands/` — 29 skills (`/morning`, `/risk`, `/profile`, …)
- `.hermes/skills/wally-skills/` — symlink a `system/skills/` (21 skills técnicas: ICT, Fibonacci, ADX, Neptune comunidad, punkchainer playbook, etc.)
- `AGENTS.md` raíz leído automáticamente por Hermes (mismo archivo que OpenCode usa)

**Conceptual mapping CC → Hermes:**
Hermes NO tiene "subagents" ni "slash commands" como filesystem entries — todo se proyecta como **skills** unificados. La invocación funciona igual: `/morning` activa la skill `wally-commands/morning`, y el agent decide cuándo invocar `wally-agents/regime-detector` según description match.

**Features únicas de Hermes (que CC/OC no tienen):**
- **Cron scheduling nativo** — `hermes cron add "0 6 * * *" /morning` para análisis automático CR 06:00
- **Multi-platform delivery** — `hermes gateway` envía análisis a Telegram/Discord/Slack/WhatsApp/Signal
- **Serverless backends** — corre en Modal/Daytona ($0 cuando idle, despierta on demand)
- **FTS5 memory search** — búsqueda full-text cross-session ("qué hice el lunes en BTC")
- **Voice memo** — mandar voz desde Telegram, Hermes transcribe
- **Skills self-improving** — skills se editan solas con uso

**Limitaciones conocidas (vs Claude Code):**
- Hooks `session_start.sh` / `stop_hook.sh` no se ejecutan automáticamente — invocar manualmente
- Statusline USD↔CRC solo en CC; en Hermes ejecutar `bash .claude/scripts/statusline.sh` manualmente
- MCP config exacta no completamente documentada upstream — usar `hermes config set` o el wizard `hermes setup`
- Subagents CC se proyectan como skills (funciona, pero pierde semántica de "subagent" explícito)

### Instalación (5 minutos)

```bash
# 1. Clonar el repo
git clone git@github.com:sasasamaes/wally-trader.git
cd wally-trader

# 2. Instalar dependencias Python core
pip3 install pyyaml

# 3. Instalar adapter Claude Code (sincroniza symlinks .claude/ → system/)
bash adapters/claude-code/install.sh

# 4. Verificar profile default (debe ser "retail" = Binance main)
bash .claude/scripts/profile.sh show
# → retail | <iso>

# 5. Verificar helpers críticos
bash .claude/scripts/fx_rate.sh                    # USD→CRC del día
bash .claude/scripts/chainlink_price.sh BTC        # precio Chainlink BTC

# 6. Abrir Claude Code y test inicial
claude
# → /status   (debe mostrar profile retail + capital + hora CR)
# → /profile  (debe listar 7 profiles: retail/retail-bingx/ftmo/fotmarkets/fundingpips/bitunix/quantfury)

# 7. Instalar TradingView MCP (ver sección "Instalar TradingView MCP" abajo)
#    Luego abrir TV Desktop con --remote-debugging-port=9222

# 8. Instalar indicador Pine en TV (manual, ~2min):
#    Pine Editor → copiar MEAN_REVERSION_INDICATOR.pine → guardar "MR Signals" → añadir al chart

# 9. (Opcional) Setup ML XGBoost — entrena 1 año BTC 15m
cd scripts/ml_system
./setup.sh
brew install libomp                                # macOS only
python3 supervised/train.py --days 365
cd ../..
# → modelo en scripts/ml_system/supervised/model/

# 10. (Opcional) Multi-CLI: OpenCode y/o Hermes
bash adapters/opencode/install.sh                  # 15 tests, soporte total v2
bash adapters/hermes/install.sh                    # 12 tests, soporte total v1
```

### Setup FTMO profile (opcional)

Si quieres operar el challenge FTMO además del retail:

```bash
# 1. Llenar credenciales FTMO en .env (gitignored)
cp .claude/.env.example .claude/.env
# Editar .claude/.env con tu editor:
#   FTMO_LOGIN=<tu login>
#   FTMO_PASSWORD=<tu password>
#   FTMO_READONLY_PASSWORD=<tu ro password>
#   FTMO_SERVER=FTMO-Demo

# 2. Abrir MT5 al menos una vez (login con cuenta FTMO-Demo)
open -a "MetaTrader 5"
# Login → cerrar

# 3. Instalar el EA ClaudeBridge.mq5 en MT5
bash .claude/profiles/ftmo/mt5_ea/install.sh
# Auto-detecta bottle path de Mac, copia EA, crea symlinks a memory/

# 4. En MT5: habilitar algo-trading + drag ClaudeBridge al chart BTCUSD
#    Tools → Options → Expert Advisors → ✅ Allow algorithmic trading
#    Navigator (Ctrl+N) → Expert Advisors → F5 → drag ClaudeBridge a chart
#    Diálogo → ✅ Allow Automated Trading → OK
#    Experts tab (Ctrl+T) debe mostrar: "ClaudeBridge EA v1.00 starting magic=77777"

# 5. Verificar heartbeat
cat .claude/profiles/ftmo/memory/mt5_state.json
# Debe tener last_update reciente
bash .claude/scripts/profile.sh set ftmo
bash .claude/scripts/statusline.sh
# [FTMO $10k] ... EA ✓ Xs

# 6. Primer test con 0.01 lots
/profile ftmo
/order BTCUSD BUY 77500 sl=77400 tp=77600 lots=0.01
# Confirmar YES → EA ejecuta → /trades muestra
```

Guía completa paso a paso: `.claude/profiles/ftmo/mt5_ea/README.md`.

### Setup Fotmarkets profile (opcional, bonus $30)

```bash
# 1. Activar bonus en Fotmarkets — registro + verificación + recibir $30
#    https://fotmarkets.com (sin depósito propio)

# 2. Recibir credenciales MT5 Standard 1:500

# 3. Login MT5 con esas credenciales una vez (igual que FTMO)

# 4. Switch profile
/profile fotmarkets
# → bash .claude/scripts/fotmarkets_guard.sh check

# 5. Verificar fase actual (default fase 1: $30→$100, risk 10%)
cat .claude/profiles/fotmarkets/memory/phase_progress.md

# 6. Workflow manual (sin EA bridge):
/morning                # análisis fase-aware
/order EURUSD BUY ...   # encola virtualmente
# Tú ejecutas manual en MT5 cuando watcher avise
```

Filosofía: capital es bonus ("casa de juego"), NO depositar dinero propio. Ver `.claude/profiles/fotmarkets/config.md`.

### Setup FundingPips profile (opcional, cuenta funded $10k)

> **⚠️ DINERO REAL desde día 1.** $99 perdido si rompes 5% DD. Estrategia ULTRA-conservadora obligatoria.

```bash
# 1. Comprar cuenta Zero $10k en https://fundingpips.com
#    Usa código HELLO → -20% → costo final $79.20 USD
#    (Add-on Swap Free opcional +$10 si harás hold overnight crypto)

# 2. Recibir credenciales MT5 por email (~minutos a horas)
#    Login + password + read-only password + server (FundingPips-Live)

# 3. Login MT5 con esas credenciales una vez
open -a "MetaTrader 5"
# Login → confirma conexión → cerrar

# 4. Llenar credenciales en .claude/.env
cp .claude/.env.example .claude/.env  # si no existe
# Editar .claude/.env y agregar:
#   FUNDINGPIPS_LOGIN=<tu login>
#   FUNDINGPIPS_PASSWORD=<tu password>
#   FUNDINGPIPS_READONLY_PASSWORD=<tu ro password>
#   FUNDINGPIPS_SERVER=FundingPips-Live

# 5. Adaptar EA ClaudeBridge.mq5 para usar magic 88888 (FTMO usa 77777)
#    Edit .claude/profiles/fundingpips/mt5_ea/config para usar magic distinto
#    O crear un segundo binary del EA con esa diferencia
#    NOTA: este paso es opcional si solo vas a operar manual sin watcher auto-fills

# 6. Switch profile y validar guardian
/profile fundingpips
# → guardian valida automáticamente al primer comando

bash .claude/scripts/fundingpips_guard.sh check --verbose
# → debe decir "✅ OK — todos los gates pasaron"

# 7. Verificar statusline
bash .claude/scripts/statusline.sh
# → [FUNDINGPIPS $10k] $10000.00 ≈₡4.5M | DD 🟢+0.00% | ...

# 8. Primer test con 0.01 lots BTCUSD o EURUSD
/profile fundingpips
/morning                       # análisis multi-asset
# Si hay setup A-grade → ejecutar manual en MT5

# 9. Después del primer trade, verificar tracking
/journal                       # debe mostrar el trade + metrics

# 10. Día 7 → primer payout disponible (si hay profit)
#     Bi-weekly cycle empieza desde compra de cuenta
```

**Workflow día 1 a día 7 (mínimo para payout):**

```
Cada día 06:00 CR:
  /profile fundingpips
  /morning                              # 17 fases multi-asset
  # Sistema scanea 20+ assets, pick 1 A-grade
  /multifactor                          # validación score >50
  /chainlink BTC                        # cross-check si crypto
  /risk-var --target-var-pct 0.5        # sizing 0.3% (cap $30 risk)

Si setup OK:
  Ejecutar 1 trade manual en MT5 (max 2/día)
  /equity <nuevo_valor>                 # tracking equity
  /journal                              # log + metrics

Si NO setup:
  Skip día (pero CONTAR como día operado SOLO si ejecutaste 1 trade)
  Tip: aunque no haya setup A-grade, ejecutar 1 micro-trade 0.01 lots
       BTCUSD para "calentar" el contador de días operados (cuesta ~$0.05
       de spread)
```

**Diferencias críticas vs FTMO:**

| Concepto | FTMO ($10k demo) | FundingPips Zero ($10k real) |
|---|---|---|
| Costo entry | $93.43 (challenge) | $99 / $79.20 con HELLO |
| Modelo | Pasa challenge → demo funded | Compras → funded directo |
| Max DD total | 10% trailing equity high | **5% del balance inicial fijo** ← más estricto |
| Consistency rule | 50% best-day cap | **15% biggest day vs total** ← formula distinta |
| Risk per trade | 0.5% | **0.3%** (más conservador) |
| Max trades/día | 3 | **2** |
| TP3 trailing | Sí (EMA20) | **NO** (incompatible con consistency) |
| Target diario | 1.5% | **0.5-0.7%** |
| Leverage | 1:100 | 1:50 |
| Payout | Variable post-eval | Bi-weekly 95% |

**Plan declarado del usuario:**
1. Comprar cuenta FundingPips Zero $10k → operar conservador 7 días min
2. Bi-weekly payout (95% del profit) → transferir a Binance para fondear retail real
3. Eventualmente: comprar otra cuenta FTMO $100k usando profits acumulados

**Recordatorios duros:**
- ⚠️ NO operar BTC/ETH simultáneo en `fundingpips` + `ftmo` + `retail` — doble exposición direccional
- ⚠️ "El edge no es ganar — es no perder." Mejor 0 trades que un trade mediocre
- ⚠️ Cualquier violación de regla → cuenta cerrada, $99 perdido

Detalles completos: `.claude/profiles/fundingpips/config.md`, `strategy.md`, `rules.md`.

### Setup Bitunix profile (opcional, copy-validated punkchainer's)

```bash
# 1. Registro en Bitunix con código de referido
#    https://bitunix.com — usa código `punkchainer` para descuento en fees

# 2. Depósito inicial $50 USDT (vía BSC/Polygon, low fee)

# 3. (Opcional) llenar credenciales API en .env si quieres tracking automático:
#    BITUNIX_API_KEY=<...>           # solo para read-only (no execution)
#    BITUNIX_API_SECRET=<...>
#    BITUNIX_REFERRAL_CODE=punkchainer

# 4. Switch profile
/profile bitunix

# 5. Acceso a comunidad punkchainer's (Discord) — los indicadores Neptune (Bangchan10)
#    son invitation-only. Sin acceso, este profile NO funciona efectivamente.
#    - Discord: solicitar invite via canal #neptune-indicators
#    - Manual oficial: docs/Neptune_Manual_Usuario_Completo.pdf

# 6. Test con primera señal (cuando aparezca en Discord)
/signal MSTRUSDT short 166.57 sl=170 tp=160 leverage=20
```

**Reglas duras Bitunix:**
- ⚠️ Override leverage **20x → 10x cap** SIEMPRE (las señales agresivas liquidan rápido a 20x)
- ⚠️ Pillars 4-pilar SMC: 4/4 = full size, 3/4 = half size, <3/4 = REJECT
- ⚠️ Daily loss -6% (3 SLs) → BLOCK día
- ⚠️ DUREX obligatorio: SL → BE en 20% recorrido o TP1 (1R en weekend)
- ⚠️ Saturday Precision Protocol activo sábado/domingo (gates más estrictos)
- ⚠️ Cross-asset BTC exclusion: NO BTC simultáneo en bitunix + retail/ftmo/fundingpips/quantfury

Detalles: `.claude/profiles/bitunix/config.md`, `strategy.md`, `rules.md`.
Skills: `@punkchainer-glossary`, `@punkchainer-playbook`, `@neptune-community-config`, `@neptune-alert-placeholders`.

### Setup Quantfury profile (opcional, BTC-denominated)

```bash
# 1. Crear cuenta en Quantfury
#    https://quantfury.com — broker app crypto-native con custodia

# 2. Depósito inicial 0.01 BTC (≈$830 a $83k/BTC, ajustable)

# 3. Switch profile
/profile quantfury

# 4. Establecer benchmark HODL (al cambio actual de BTC/USD)
#    El sistema trackea PnL en BTC absoluto y compara vs HODL pasivo
bash .claude/scripts/btc_outperform.py --init 0.01

# 5. Análisis régimen-aware (mismo que retail pero BTC-denominated)
/morning
```

**Reglas duras Quantfury:**
- ⚠️ Métricas TODAS en BTC (no USD) — incluye Sharpe, max DD, daily PnL
- ⚠️ Outperformance vs HODL **es la métrica clave** — si trading <-2% vs HODL mensual → PAUSAR 30d
- ⚠️ Risk 2% del BTC capital (0.0002 BTC en 0.01)
- ⚠️ Leverage cap 5x effective (no 10x)
- ⚠️ Daily BTC PnL -2% → BLOCK día. Total DD -10% → BLOCK profile.
- ⚠️ Régimen TRENDING UP → prefiere HODL pasivo > longs activos
- ⚠️ Cross-asset BTC exclusion: NO BTC simultáneo con otros profiles

Helper único: `bash .claude/scripts/btc_outperform.py --period 30d`
Detalles: `.claude/profiles/quantfury/config.md`, `strategy.md`, `rules.md`, `memory/hodl_benchmark.md`.

### Setup OpenCode (opcional, hedge multi-CLI)

```bash
# 1. Instalar OpenCode
curl -fsSL https://opencode.ai/install | bash

# 2. Generar .opencode/ + opencode.json (raíz) desde system/ + git pre-commit hook
bash adapters/opencode/install.sh

# 3. Verificar (15 tests)
python3 -m pytest adapters/opencode/test_opencode_transform.py -v

# 4. (Opcional) Real-time sync durante edición activa
brew install fswatch
bash adapters/opencode/watch.sh   # daemon en terminal aparte

# 5. Probar dentro del repo
cd ~/Documents/wally-trader
opencode
# → dentro de OpenCode: /status, /morning, /risk, etc.
# OC lee automáticamente AGENTS.md + CLAUDE.md
```

Detalles + tabla de diferencias OC vs CC en `adapters/opencode/README.md`.

### Setup Hermes Agent (opcional, multi-CLI con cron + delivery)

```bash
# 1. Instalar Hermes
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

# 2. Generar .hermes/skills/ desde system/ + symlink a ~/.hermes/skills/wally-trader/
bash adapters/hermes/install.sh

# 3. Verificar (12 tests)
python3 -m pytest adapters/hermes/test_hermes_transform.py -v

# 4. Setup Hermes (model + provider — requiere cuenta API tipo OpenRouter)
hermes setup

# 5. (Opcional) Configurar TradingView MCP en Hermes
hermes config set mcp.tradingview.command node
hermes config set mcp.tradingview.args '["./tradingview-mcp/src/server.js"]'

# 6. Lanzar
cd ~/Documents/wally-trader
hermes
# → Hermes lee AGENTS.md + carga 12 agents + 33 commands + 17 skills
```

**Use cases únicos de Hermes (vs CC/OC):**
- `hermes cron add "0 6 * * *" /morning` → análisis automático CR 06:00 sin abrir laptop
- `hermes gateway setup` → recibir alertas en Telegram/Discord/WhatsApp
- Backend serverless (Modal/Daytona) → corre 24/7 hibernando, costa centavos

Detalles en `adapters/hermes/README.md`.

### Correr todos los tests del adapter (verificación)

```bash
python3 -m pytest adapters/ -v
# 27 tests pasando: 15 OpenCode + 12 Hermes
```

### Instalar TradingView MCP (prompt listo para Claude Code)

Copia este prompt tal cual a Claude Code (o a Claude Desktop) en una sesión nueva. Claude ejecuta paso por paso y te reporta cada etapa:

```text
Quiero conectar mi app de TradingView a Claude Code usando el MCP de @Tradesdontlie.
Repo oficial: https://github.com/tradesdontlie/tradingview-mcp

Por favor haz TODO esto paso por paso, reportándome cada etapa. No avances al
siguiente paso si uno falla — explícame el error y cómo resolverlo.

1. VERIFICAR PRERREQUISITOS:
   - Corre "node --version" — tengo que tener Node.js 18 o mayor. Si me falta o es
     muy viejo, dime exactamente cómo instalarlo para mi sistema operativo.
   - Corre "git --version" — si no tengo Git, dime cómo instalarlo.
   - Pregúntame si ya tengo TradingView Desktop instalado. Si no, mándame el link
     oficial: https://www.tradingview.com/desktop/

2. CLONAR EL REPO:
   Clona el repositorio en mi carpeta home:
   git clone https://github.com/tradesdontlie/tradingview-mcp.git ~/tradingview-mcp

3. INSTALAR DEPENDENCIAS:
   Entra a la carpeta y corre la instalación:
   cd ~/tradingview-mcp && npm install

4. LEER EL README:
   Lee el README.md del repo para identificar:
   - El comando exacto para iniciar el servidor MCP (puede ser "node src/server.js"
     o algo distinto según la versión).
   - El flag de debug para lanzar TradingView (suele ser --remote-debugging-port=9222).
   - Si hay scripts de lanzamiento en la carpeta "scripts/" que yo deba usar directo.

5. CONFIGURAR EL MCP EN CLAUDE CODE:
   Edita mi archivo de configuración de MCPs. Ubicación según mi OS:
   - macOS / Linux: ~/.claude/.mcp.json
   - Windows: %USERPROFILE%\.claude\.mcp.json

   Si el archivo no existe, créalo. Si ya existe con otros MCPs, NO los sobrescribas
   — solo agrega el de tradingview dentro de "mcpServers". El bloque a insertar
   (ajusta la ruta absoluta con mi carpeta real):

   {
     "mcpServers": {
       "tradingview": {
         "command": "node",
         "args": ["/ruta/absoluta/a/tradingview-mcp/src/server.js"]
       }
     }
   }

6. LANZAR TRADINGVIEW CON DEBUG PORT:
   Explícame cómo cerrar completamente TradingView y volverlo a abrir con el flag
   de debug. Dame el comando exacto para mi sistema operativo. Si el repo incluye
   un script en scripts/ (por ejemplo launch_tv_debug_mac.sh), úsalo y dime cómo
   correrlo.

7. DECIRME QUÉ HAGO AHORA:
   Resume en 3 pasos finales lo que me toca hacer:
     (a) reiniciar Claude Code
     (b) abrir una conversación nueva
     (c) correr el primer prompt de verificación
   Dame el prompt exacto para el paso (c).

Objetivo final: que cuando abra Claude Code y escriba "Corre tv_health_check",
me responda cdp_connected: true. Ahí sabemos que jaló.
```

**Qué hace el prompt:** verifica Node/Git, clona el MCP al home, instala deps, lee el README del upstream, edita `~/.claude/.mcp.json` sin borrar otros servers, lanza TV con `--remote-debugging-port=9222`, y termina con un health check. Objetivo: `tv_health_check` devuelve `cdp_connected: true`.

**Alternativa manual** (si prefieres no usar el prompt): seguir `tradingview-mcp/README.md` del submodule y agregar el server con `claude mcp add tradingview node /absolute/path/to/tradingview-mcp/src/server.js`.

### Instalar Notion MCP — dual-write de journal a Notion (prompt listo para Claude Code)

Opcional pero recomendado si quieres que cada trade se loggee **tanto en `.md` local como en Notion**. El sistema detecta la config automáticamente — si no configurás Notion, sigue funcionando con solo `.md`.

Copia este prompt tal cual a Claude Code en una sesión nueva. Claude ejecuta paso por paso, crea las DBs via MCP, y te reporta cada etapa:

```text
Quiero conectar Notion MCP al sistema de trading para dual-write de journal
(retail + FTMO). Repo: este mismo (~/Documents/trading). Docs de referencia:
docs/NOTION_SETUP.md del repo.

Por favor haz TODO esto paso por paso, reportándome cada etapa. No avances al
siguiente paso si uno falla — explícame el error y cómo resolverlo.

1. VERIFICAR PRERREQUISITOS:
   - Verifica que estamos en la raíz del repo: `pwd` debe ser ~/Documents/trading
     (o donde clonaste). Si no, `cd` ahí primero.
   - Verifica que tengo cuenta de Notion activa. Preguntame si no lo sabes.
   - Verifica Node.js 18+: `node --version`. Si falta, dime cómo instalarlo.

2. INSTALAR EL NOTION MCP OFICIAL (OAuth):
   Corre: `claude mcp add notion https://mcp.notion.com/mcp`
   Esto va a abrir OAuth flow en el browser:
     - Te voy a pedir login a Notion
     - Autorizar acceso al workspace que usaré para las DBs
   Espera a que complete. Luego verifica con:
   `claude mcp list | grep notion`
   Debe mostrar: "notion: https://mcp.notion.com/mcp - ✓ Connected"
   Si no conecta, retry una vez. Si sigue fallando, diagnostica el error.

3. CREAR LAS 2 NOTION DBs VIA MCP:
   Ahora que el MCP está conectado, usá las tools mcp__notion__* para crear
   2 databases en mi workspace. Primero preguntame en qué página quiero que
   vivan (raíz del workspace o una página específica). Luego:

   DB 1: "Trades Retail" con schema (exacto):
     - Name (Title)
     - Date (Date)
     - Time CR (Text)
     - Asset (Select: BTCUSDT.P)
     - Direction (Select: LONG, SHORT)
     - Entry (Number)
     - SL (Number)
     - TP1 (Number)
     - TP2 (Number)
     - TP3 (Number)
     - Size (BTC) (Number)
     - Leverage (Number)
     - Result (Select: TP1, TP2, TP3, SL, BE, partial, open)
     - PnL $ (Number)
     - PnL % (Number)
     - R multiple (Number)
     - Filters passed (Text)
     - ML score (Number)
     - Sentiment (Number)
     - Notes (Text)

   DB 2: "Trades FTMO" con schema (exacto):
     - Name (Title)
     - Date (Date)
     - Time CR (Text)
     - Asset (Select: BTCUSD, ETHUSD, EURUSD, GBPUSD, NAS100, SPX500)
     - Direction (Select: LONG, SHORT)
     - Entry (Number)
     - SL (Number)
     - TP1 (Number)
     - TP2 (Number)
     - Lots (Number)
     - Magic (Number)
     - Ticket MT5 (Number)
     - Status (Select: queued, sent_to_ea, filled, expired, canceled, manual_pending, closed)
     - Result (Select: TP1, TP2, SL, BE, partial, open, N/A)
     - PnL $ (Number)
     - PnL % (Number)
     - R multiple (Number)
     - Filters passed (Text)
     - Guardian verdict (Select: OK, OK_WITH_WARN, BLOCK_SIZE, BLOCK_HARD, override)
     - Equity pre (Number)
     - Equity post (Number)
     - Notes (Text)

   Reporta los 2 database_id generados (hex 32 chars cada uno).

4. LLENAR .env CON LOS DB IDs:
   - Si no existe .claude/.env, crealo copiando de .env.example:
     `cp .claude/.env.example .claude/.env`
   - Edita .claude/.env y agrega/actualiza estas dos líneas con los IDs del paso 3:
     NOTION_RETAIL_DB_ID=<id_db_retail>
     NOTION_FTMO_DB_ID=<id_db_ftmo>
   - Verificá que .env NO está en git: `git status --short` — .env no debe aparecer.

5. VERIFICAR DETECCIÓN:
   Corre: `bash .claude/scripts/statusline.sh`
   El output debe terminar con "• 📝 Notion ✓". Si no, revisá paso 4 y relee.

6. TEST DE DUAL-WRITE:
   - Cambia a profile retail: `bash .claude/scripts/profile.sh set retail`
   - Simula un trade cerrado: invoca /journal y dime qué parámetros te pido
     para crear una entrada de prueba (trade #TEST con capital unchanged).
   - Al ejecutar /journal, deberías:
     (a) Append al .md local
     (b) Crear una row nueva en Notion DB Trades Retail
     Verificá visualmente ambos. Si falla Notion, reporta el error exacto
     y dejá el .md local intacto.
   - Al terminar exitoso, borra el row de prueba de Notion (fue solo test)
     y revierte el append del .md.

7. DECIRME QUÉ HAGO AHORA:
   Resume en 3 pasos:
     (a) recarga/reinicia Claude Code si el statusline no mostraba el tag
     (b) uso normal: cada /journal, /order, /sync, /trades, /challenge ahora
         hace dual-write transparente (sin pedirme nada extra)
     (c) si quiero desactivar Notion temporalmente: comentar las líneas en
         .env o borrarlas

Objetivo final: que cuando corra /journal en modo retail con un trade real,
aparezca un row nuevo en la DB "Trades Retail" en mi Notion, y el .md local
también tenga el append. Ahí sabemos que funciona.
```

**Qué hace el prompt:** conecta Notion MCP via OAuth, crea las 2 DBs (retail + ftmo) directamente desde Claude con el schema correcto (sin copiar/pegar manual), actualiza `.env` con los IDs, verifica detección via statusline, y prueba end-to-end con un trade dummy. Todo lo que no requiere UI del browser, lo automatiza.

**Alternativa manual** (si prefieres hacer las DBs a mano): seguir `docs/NOTION_SETUP.md` paso a paso — incluye schemas con checkboxes y troubleshooting.

### Memoria persistente

Claude mantendrá memoria de tu perfil en `~/.claude/projects/.../memory/`.
**Importante:** esa carpeta NO está en este repo (excluida por `.gitignore`).
Si cambias de máquina, deberás regenerar la memoria o copiarla manualmente.

---

## 📊 Progreso y objetivos

### Ruta planificada

| Meta | Capital | Días estimados | Estado |
|---|---|---|---|
| Primer trade ganador | $10 → $11.14 | 1 | ✅ **Completado** (2026-04-20) |
| Segundo trade ganador | $11.14 → $12.23 | 1 | ✅ **Completado** (2026-04-21) |
| Tercer trade ganador | $11.82 → $13.63 | 1 | ✅ **Completado** (2026-04-22, +15.32%) |
| Acumular 25 trades estadísticos | → $15-20 | ~15-20 | 🔄 En progreso (3/25) |
| WR validado ≥ 60% sobre 25+ trades | — | ~20 | ⏳ Pendiente |
| $20 por trade | $161 cap | ~26 | ⏳ Pendiente |
| $50/día promedio | $325 cap | ~70 | ⏳ Pendiente |
| **$100/día promedio** | **$650 cap** | **~85** | ⏳ Pendiente |
| FTMO $10k fundeado | — | ~60 post-validación | ⏳ Pendiente |

### Métricas objetivo mínimo (después de 25 trades)

- Win Rate ≥ 60%
- Profit Factor ≥ 1.8
- Max Drawdown ≤ 15%
- Days operated ≥ 15

---

## 🧠 Principios del sistema

### 1. Régimen dicta estrategia
Una estrategia no es universal. **Mean Reversion** funciona en RANGE. **Donchian Breakout** funciona en TRENDING. Cada día detectar el régimen antes de elegir.

### 2. 4 filtros obligatorios
Nunca entrar con 3/4 filtros. La disciplina es el edge.

### 3. Position sizing 2% fijo
Nunca arriesgar más del 2% del capital por trade. Matemáticamente imposible quebrar con 60%+ WR.

### 4. Stop de sesión duro
2 SLs consecutivos → para el día. No hay "recuperación".

### 5. Journal obligatorio
Cada trade se documenta. Sin journal no hay mejora.

### 6. Disciplina > Estrategia
El 90% de retail pierde por emocional, no por análisis. Tu mayor enemigo eres tú.

---

## 📚 Archivos clave y para qué sirven

### `CLAUDE.md`
Guía principal que Claude lee al iniciar sesión. Contiene perfil del trader, estrategia activa, reglas, niveles técnicos vigentes, APIs útiles.

### `MORNING_PROMPT.md` ⭐
**El archivo más importante.** Contiene:
- Prompt completo de 17 fases para copy-paste cada mañana
- Checklist físico imprimible
- Templates de journal diario y review semanal
- Quick commands
- Mantras del día

### `MEAN_REVERSION_INDICATOR.pine`
Código Pine Script del indicador con los 4 filtros automatizados. Se pega en TradingView → Pine Editor.

Incluye:
- Donchian(15) channel
- Bollinger Bands(20, 2)
- RSI(14) OB/OS
- ATR(14) para SL/TP dinámicos
- Flechas LONG/SHORT cuando 4/4 filtros alinean
- Tabla top-right con status de filtros en tiempo real
- Alertas configurables

### `DAILY_TRADING_JOURNAL.md`
Template para registrar cada trade con todos sus datos. Obligatorio.

### `RISK_CALCULATOR.md`
Fórmulas de position sizing, cálculo de SL/TP basado en capital.

### `.claude/agents/` — 7 Agentes especializados

Claude detectará automáticamente cuál invocar según tu pregunta:

| Agente | Se activa cuando preguntas... |
|---|---|
| **morning-analyst** | "análisis matutino", "morning analysis", "empezar sesión" |
| **trade-validator** | "¿entro?", "valida entry", "4 filtros alineados?" |
| **regime-detector** | "¿qué régimen?", "¿range o trend?", "qué estrategia uso" |
| **chart-drafter** | "dibuja niveles", "actualiza chart", "limpia y redibuja" |
| **risk-manager** | "cuánto abro", "size del trade", "position sizing" |
| **journal-keeper** | "cierro día", "journal", "log trade", "review semana" |
| **backtest-runner** | "backtest X", "probar esta config", "grid search" |
| **technical-analyst** | "TA profundo", "smart money", "armónico", "elliot", "fibonacci" |
| **signal-validator** | "valida señal", "[comunidad] dice...", "/signal Short XLM" |

### `system/commands/` — 33 Slash commands (profile-aware)

Atajos rápidos. La mayoría se adaptan al profile activo automáticamente.

**Dual-profile (nuevos):**

| Comando | Acción |
|---|---|
| `/profile` | Ver/cambiar profile activo (retail/ftmo) |
| `/status` | Estado profile-aware (retail: cap/régimen; ftmo: equity/DD/EA) |

**FTMO-only:**

| Comando | Acción |
|---|---|
| `/equity <valor>` | Actualizar equity FTMO desde MT5 |
| `/challenge` | Dashboard progreso challenge (profit, rules, best day ratio) |
| `/order` | Encolar orden al EA (con YES typed obligatorio) |
| `/trades` | Dashboard MT5 (posiciones, pendientes, closed today) |
| `/sync` | Reconciliar pending_orders.json ↔ mt5_state.json |

**Trading core (profile-aware):**

| Comando | Acción |
|---|---|
| `/morning` | Despacha morning-analyst (retail 17 fases) o morning-analyst-ftmo (14 fases multi-asset) |
| `/validate` | Retail: 4 filtros + ML opcional. FTMO: 7 filtros + guardian check_entry |
| `/regime` | Detecta régimen rápido (RANGE/TRENDING/VOLATILE) |
| `/risk` | Position sizing — 2% retail, 0.5% FTMO (via guardian) |
| `/journal` | Retail: tradicional. FTMO: auto-ingest closed_today del EA |
| `/chart` | Limpia y redibuja niveles en TV |
| `/backtest` | Ejecuta backtest/grid search |
| `/review` | Review semanal con métricas |
| `/levels` | Niveles técnicos actuales |
| `/alert` | Configura alerta custom |

**Análisis técnico avanzado:**

| Comando | Acción |
|---|---|
| `/ta` | Análisis técnico avanzado (ICT, armónicos, chartismo, Elliott, Fibonacci) |
| `/signal` | Valida señal externa de comunidad (GO/NO-GO) |
| `/neptune` | Lee outputs de indicadores Neptune (Bangchan10) |

**Capa ML:**

| Comando | Acción |
|---|---|
| `/sentiment` | NLP Sentiment Aggregator (F&G + News + Reddit + Funding) → score 0-100 |
| `/ml` | ML score del setup actual (XGBoost, probabilidad TP-first) |
| `/ml-train` | Re-entrena el modelo XGBoost con histórico Binance |

### `system/skills/` — 21 Skills custom

**Análisis técnico avanzado (metodologías):**
- **smart-money-ict** — Order Blocks, Fair Value Gaps, Liquidity, BoS/ChoCh, Premium/Discount
- **harmonic-patterns** — Gartley, Bat, Butterfly, Crab, Shark, Cypher con Fibonacci
- **classic-chartism** — H&S, triangles, flags, wedges, double/triple tops
- **elliott-waves** — 5-impulsivo + 3-correctivo con Fibonacci targets
- **fibonacci-tools** — Retracements, extensions, time zones, confluencia MTF

**Indicadores técnicos:**
- **stochastic-oscillator** — Full/Slow/Stoch RSI, crossovers, divergencias
- **bollinger-bands-advanced** — Squeeze, walking band, %B, bandwidth, TTM
- **adx-trend-strength** — ADX, +DI/-DI para fuerza y dirección de tendencia
- **divergence-analysis** — Regular/hidden, bull/bear, clase A/B/C con RSI/MACD/OBV
- **trendlines-sr** — Soportes, resistencias, trendlines, canales, breakouts vs fakeouts

**Indicadores de comunidad punkchainer's (Neptune by Bangchan10):**
- **neptune-indicators** — Lectura conceptual outputs Neptune Signals/Oscillator/SMC/Money Flow/Pivots
- **neptune-community-config** 🆕 — Configs EXACTAS validadas (Sensitivity MANUAL, Money Flow "Smart Money", Modern UI ON, Anomalies Signals)
- **neptune-alert-placeholders** 🆕 — Placeholders + JSON templates para webhooks 3Commas/Cornix

**Playbooks operativos comunidad punkchainer's:**
- **punkchainer-glossary** 🆕 — Glosario SMC/ICT + términos exclusivos comunidad: **DUREX** (mover SL a BE en 20% recorrido o TP1) y **GORRAS** (filtro anti-fake gurus)
- **punkchainer-playbook** 🆕 — 4-Pilar Entry Checklist Neptune SMC (LONG/SHORT) + Saturday Precision Protocol (rules estrictos weekend) + Reglas de Oro (no perseguir, filtro Adjusted, alts +0.5%)

**Cross-source validation cuantitativa:**
- **chainlink-cross-check** 🆕 — Validar precio TV vs Chainlink Data Feeds (oráculo on-chain) — detecta wicks fakeados, feed stale, divergencia exchange
- **multifactor-scoring** 🆕 — Score 0-100 cuantitativo (Momentum + Volatility + Trend + Volume) complementario al ML XGBoost
- **risk-quant** 🆕 — VaR/CVaR sizing adaptativo + Risk Parity multi-asset (FTMO/fotmarkets)

**Análisis contextual:**
- **btc-regime-analysis** — Deep dive de régimen con MTF + divergencias + cycle analysis
- **btc-on-chain** — Análisis on-chain (hashrate, flows, whales, MVRV)
- **trade-psychology** — Framework para manejar tilt, FOMO, revenge trading, overconfidence

### `.claude/scripts/` — Automatización

- **statusline.sh** — Status line siempre visible: `💰 $13.63 (+$3.63) │ 📊 0/3 │ 🟢 VENT │ 🕐 CR 06:00 │ BTC.P`
- **session_start.sh** — Carga contexto al iniciar Claude (capital, reglas, comandos)
- **stop_hook.sh** — Auto-commit del journal al cerrar sesión
- **preprompt_check.sh** — Detecta "arriesgar todo", "mover SL", "aumentar leverage" y alerta
- **notify.sh** — Notificaciones nativas macOS
- **alert_setup.sh** — Monitor de setup 4/4 en background
- **daily_cron.sh** — Recordatorio matutino 5:30 AM (vía cron/launchd)

### Hooks configurados en `settings.json`

| Hook | Acción |
|---|---|
| **SessionStart** | Inyecta contexto trading automáticamente |
| **Stop** | Auto-commit del journal si hay cambios |
| **UserPromptSubmit** | Detecta palabras de auto-sabotaje y advierte |

### Status line persistente

Siempre visible en tu terminal:

```
💰 $13.63 (+$3.63) │ 📊 0/3 │ 🟢 VENT │ 🕐 CR 06:00 │ BTC.P
```

Muestra: capital actual, delta desde inicial, trades hoy, si estás en ventana, hora CR, símbolo.

---

## 🔄 Workflow con Git

### Commit diario del journal
```bash
git add DAILY_TRADING_JOURNAL.md
git commit -m "journal: 2026-04-21 +$1.20 (+12.4%)"
git push
```

### Commit de cambios de estrategia
```bash
git add CLAUDE.md MORNING_PROMPT.md
git commit -m "strategy: ajustar filtro RSI tras review semanal"
git push
```

### Commit de nuevos backtest findings
```bash
# Los backtests corren en /tmp/ y NO se commitean.
# Solo los hallazgos se documentan en memoria de Claude
# o en markdowns específicos si son relevantes.
```

---

## ⚠️ Disclaimers importantes

1. **Esto NO es consejo financiero.** Todo lo aquí descrito es para fines educativos y de investigación personal.

2. **Futuros con leverage pueden liquidar capital en minutos.** Usa solo capital que puedas perder sin afectar tu vida.

3. **Win Rate histórico ≠ Win Rate futuro.** Los backtests tienen data limitada (3-50 días según TF). Validación real requiere 25+ trades live.

4. **El sistema depende de disciplina.** Saltarte filtros o mover SLs convierte un sistema ganador en perdedor.

5. **El mercado cambia.** Si regime shift no detectado → recalibrar estrategia. Revisa régimen semanalmente.

---

## 🛠️ Troubleshooting

### Claude no recuerda mi capital/progreso
- Verifica que exista `~/.claude/projects/<project-path-encoded>/memory/`
- Lee `MEMORY.md` — debe listar todas las memorias activas
- Si falta, pide a Claude: "lee mi memoria y cárgala"

### El indicador Pine no aparece en TradingView
- TV Basic limita a 2 indicadores por chart
- Quita uno (Neptune Signals o Oscillator) primero
- Luego añade MR Signals

### draw_clear falla con "getChartApi is not defined"
- Workaround: click derecho en trash icon del left sidebar
- Menú contextual → "Eliminar dibujos"
- Documentado en `~/.claude/.../tradingview_setup.md`

### Pine Editor hang/loading infinito
- Cierra el panel y reabre
- Si persiste, guarda el código localmente (ya está en `MEAN_REVERSION_INDICATOR.pine`) y pega manual

---

## 🤝 Colaboración

PRs bienvenidos. Lee **[CONTRIBUTING.md](CONTRIBUTING.md)** antes de empezar — incluye tipos de contribución aceptadas, reglas de seguridad (nunca commitear credenciales), convenciones de commit, y el scope del proyecto.

**Issues y feature requests:** usa los [templates](.github/ISSUE_TEMPLATE/) del repo para bug reports y feature requests.

---

## 📜 Licencia

Este proyecto está licenciado bajo **[MIT License](LICENSE)**.

En resumen: puedes usar, modificar, distribuir y vender este código libremente con o sin atribución, siempre que (a) incluyas el copyright + licencia, y (b) entiendas que se provee "as is" sin garantías.

**Nota adicional:** el código se comparte con fines educativos e investigación. Nada aquí constituye consejo financiero. Ver disclaimer completo en [LICENSE](LICENSE).

---

## 🙏 Créditos

- **Estrategia Mean Reversion / Donchian Breakout:** construida iterativamente vía backtests
- **Indicadores Pine Script:** escritos en Pine v6
- **TradingView MCP:** [tradingview-mcp](https://github.com/anthropics/claude-code/tree/main/examples/tradingview) (o equivalente)
- **Claude Code:** [Anthropic](https://claude.com/claude-code)

---

## 💎 Mantra del sistema

> **"El mejor trade del año es el que NO hiciste por falta de setup."**
>
> **"Un SL pequeño respetado es una victoria. Un SL movido es el principio del fin."**
>
> **"Tu cuenta crece por lo que NO haces, tanto como por lo que haces."**

---

**Última actualización:** 2026-04-23 (sesión arquitectura — 3 features nuevos, 66 commits)
**Capital actual (retail):** $13.63 (3/3 wins, +36.3% acumulado)
**Estado FTMO:** profile + MT5 bridge implementados, pendiente paper trading en Free Trial
**Próximo objetivo retail:** $20 (≈ +63%) en las próximas 2 semanas
**Próximo objetivo FTMO:** correr backtest → paper trading 10+ trades → decidir challenge $93

**Features recientes:**
- Dual-profile system (retail + FTMO) — commit `086e754`
- MT5 Bridge con EA MQL5 — commit `c27ccf6`
- Multi-CLI portability (system/ + adapters OC/Codex) — commit `c3eda3a`
- Capa ML (Sentiment NLP + XGBoost + LSTM scaffold) — commit `fa06770`

**Tests totales:** 54 unit (24 guardian + 19 mt5_bridge + 11 transform) + 8 integration e2e.
