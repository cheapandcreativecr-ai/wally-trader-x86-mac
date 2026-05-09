# Changelog

Versionado semántico de cambios significativos en strategy/risk/system. Notable
changes que afectan trading decisions, profile rules, o backtest hallazgos. Para
historial completo de commits, ver `git log`.

Formato: [Keep a Changelog](https://keepachangelog.com/) + [SemVer](https://semver.org/).

⚠️ **Strategy/risk changes son MAJOR** porque pueden afectar capital real.

## v2.0 — 2026-05-08

### Phase 1: Trade entry safety net (`4b70950`)
- `portfolio.py`: heat tracking + correlation guard + breach detection
- `atr_sl.py`: volatility-adjusted SL with regime-aware multipliers
- `risk.auto_levels()`: combined SL/TP/leverage cap helper
- 2 new MCP tools: `portfolio_heat`, `auto_sl_tp`

### Phase 2: Discipline & tilt (`ffac46f`)
- `discipline.py`: tilt detector (4 components), forced cooldown, pre-trade checklist
- 3 new scripts: `tilt_check.py`, `checklist.py`, `why_this_trade.py`
- New agent: `discipline-coach`
- 1 new MCP tool: `tilt_check`

### Phase 3: Calibration & signal reliability (`53b2022`)
- `calibration.py`: live vs backtest divergence detection
- `divergence_check.py`, `stale_guard.py`, `journal_autofill.py`
- 2 launchd plists: macro-refresh (6h), journal-autofill (23:55 CR)
- 1 new MCP tool: `divergence_check`

### Phase 4: Web dashboard (`2d602a8`)
- FastAPI server at localhost:8080 with 8 endpoints
- Single-page vanilla-JS dashboard (dark theme, 5s polling)
- launchd daemon support via `make dashboard-install`
- New optional `[dashboard]` extra (fastapi, uvicorn, httpx)

### Phase 5: Notifications + ingestion (`f4eff52`)
- Real Telegram (no SDK, urllib-based) with inline keyboard support
- `source_grader.py`: A/B/C/F per signal source
- `funding_alerts.py`: extreme funding detection
- `screenshot_on_entry.py`: macOS screencapture at trade entry
- `/correl` slash command + `correlation_report` MCP tool

### Phase 6: Reliability ops (`b122fd8`)
- `ops.py`: HealthCheck + run_all_checks (5 sub-checks)
- 4 new scripts: `health_daemon.py`, `backup_daily.py`, `mcp_watchdog.sh`, `sync_drift_check.py`
- 3 launchd plists: health (60s), backup (03:00 CR), mcp-watchdog (2min)
- 1 new MCP tool: `ops_health`

### Phase 7: Financial accountability (`64f3a58`)
- `audit.py`: SHA256-chained tamper-evident log
- 3 new scripts: `tax_tracker.py`, `risk_disclosure.py`, `margin_call_sim.py`
- `docs/DISASTER_RECOVERY.md` runbook
- 1 new MCP tool: `margin_sim`

### Phase 8: Habits + ASCII charts (`8b58ba7`)
- `habit_tracker.py`: 6-habit daily check-in + streak math
- `ascii_chart.py`: Unicode-block sparklines
- 2 slash commands: `/habit`, `/ascii`

### Phase 9: Mobile + voice + Notion templates (`d0638a1`)
- PWA support: manifest.json + service worker + mobile API key auth
- `voice_listener.py`: wake word "hermes" + 8 phrase mappings (Windows)
- `notion_init.py`: `--template dashboard` mode
- `docs/IOS_PWA.md` setup guide

### Phase 10: Stabilization (this commit)
- Updated `README.md` v2 features section
- This `CHANGELOG.md`
- DR drill verification
- Security pass on .gitignore
- 207 tests green

## v1.x — pre-2026-05-08

See git history before commit `4b70950` for v1 evolution.

---

## [Unreleased]

### Added
- **CI/CD pipeline** (GitHub Actions): tests pytest matrix Python 3.9/3.11/3.12 × ubuntu/macos/windows + ruff lint + adapter sync verification
- **CHANGELOG.md** (este archivo) — versionado semántico de strategy/risk
- **Cross-profile risk guard** (`cross_profile_guard.py`): detecta automáticamente exposición misma asset+side en múltiples profiles → BLOCK. Reemplaza la regla "no BTC simultáneo" mental por enforcement Python
- **pytest suite** completa para canonical scripts: 49 tests cubriendo profile/fotmarkets_phase/fx_rate/chainlink_price/notify + 19 tests cross_profile_guard = **68 unit tests**
- **Slash commands → Python directo** (eliminado dep `bash`): los 33 slash commands ahora usan `python3 .claude/scripts/X.py` en vez de `bash X.sh` → funciona sin Git Bash en Windows nativo

### Changed
- `fotmarkets_guard.sh` y `fundingpips_guard.sh` ahora delegan a sus equivalentes Python (lógica idéntica, output bit-perfect)

## [2.4.0] - 2026-04-30 — Cross-platform full support

### Added
- **`profile.py`, `fotmarkets_phase.py`, `fx_rate.py`, `chainlink_price.py`, `notify.py`** — Python canonical implementations (single source of truth)
- **Wrappers Windows nativos** (`.claude/scripts/win/*.cmd`, `*.ps1`): cmd.exe / PowerShell sin Git Bash
- **`setup.py` universal installer**: autodetecta OS, instala deps, genera adapters, smoke test
- **`setup.sh`** bash launcher para macOS/Linux/Windows-Git-Bash
- **README sección "Cross-platform support"**: matriz macOS/Linux/Windows × CC/OpenCode/Hermes

### Changed
- Todos los bash scripts (`profile.sh`, `fotmarkets_phase.sh`, `fx_rate.sh`, `chainlink_price.sh`, `notify.sh`) reducidos a thin wrappers que delegan a Python canonical

## [2.3.0] - 2026-04-30 — Backtest findings + per-asset strategy mapping

### Added
- **Backtest unificado 7 profiles** (`docs/backtest_findings_2026-04-30.md`): 60 días, OOS 70/30 split
- **Engine Python vectorizado** (`/tmp/wally_backtest/engine.py` + `engine_v2.py`): Mean Reversion, Donchian Breakout, MA Crossover, regime gate ADX
- **Per-asset strategy mapping** (FTMO + FundingPips): basado en evidencia backtest
- **Bitunix tracking template extendido**: `signals_received.md` 8-step pipeline + `signals_received.csv` schema

### Changed (BREAKING — strategy)
- **Regime gate ADX<20 HARD precondition** (retail/retail-bingx/quantfury Mean Reversion). Sin gate: -34.83% Ret. Con gate: -4.01% (88% loss reduction)
- **Fotmarkets risk fase 1: 10% → 1%** (backtest demostró DD 70% a 10%, DD 10.53% a 1%)
- **Fotmarkets fase 1 whitelist**: removido GBPUSD (sin edge a ningún risk level)
- **Quantfury HODL pre-flight obligatorio**: regla "<-2% mensual → PAUSAR 30d" se activaría inmediatamente en período actual (-49.81pp vs HODL)

### Strategy mapping per-asset (FTMO/FundingPips)
| Asset | Strategy ganadora | TF | WR | PF |
|---|---|---|---|---|
| XAUUSD ⭐ | Donchian Breakout | 4H | 66.67 | 2.175 |
| USDJPY | MA Crossover (9/21) | 1H | 55.17 | 1.861 |
| EURUSD | Donchian Breakout | 1H | 55.17 | 1.357 |
| BTCUSDT/ETH | Mean Reversion | 1H | 31.25 | 1.048 |
| GBPUSD ❌ | (sin edge) | — | — | — |

## [2.2.0] - 2026-04-30 — Punkchainer playbook + 4-pilar SMC

### Added
- **`punkchainer-playbook` skill**: 3 protocolos comunidad (4-Pilar Entry Checklist Neptune SMC, Saturday Precision Protocol, Reglas de Oro)
- **Bitunix pipeline 8-step**: parse → 4 filtros → MF/ML → Chainlink → régimen → 4-pilar SMC → Saturday Protocol → veredicto
- **Anomalies Signals** documentado en `neptune-community-config` skill (LSMA-based divergence detection)

### Changed
- DUREX rule en bitunix: trigger weekday 20% recorrido vs weekend 1R
- Pipeline `/signal` agent ahora respeta Saturday Protocol con gates más estrictos

## [2.1.0] - 2026-04-30 — Bitunix + Quantfury profiles

### Added
- **Profile bitunix** ($50, copy-validated punkchainer's community)
- **Profile quantfury** (0.01 BTC, BTC-denominated trading)
- **`punkchainer-glossary` skill** (DUREX rule, GORRAS filter, SMC/ICT terminology)
- **`neptune-community-config` skill** (configs exactas indicadores Neptune)
- **`neptune-alert-placeholders` skill** (webhooks JSON templates)
- **`btc_outperform.py`** helper para Quantfury HODL benchmark

### Changed
- Cross-asset BTC exclusion rule añadida a CLAUDE.md (no BTC simultáneo en múltiples profiles)
- README: 5 profiles → 7 profiles, 14 skills → 21 skills, 23 commands → 33 commands

## [2.0.0] - 2026-04-29 — Multi-CLI support (OpenCode + Hermes)

### Added
- **OpenCode adapter v2** (`adapters/opencode/transform.py` + `opencode.json` raíz + `AGENTS.md`)
- **Hermes Agent adapter v1** (`adapters/hermes/transform.py` — agentskills.io standard)
- Pre-commit hook auto-sync de adapters

### Changed
- `system/` consolidado como single source of truth para todos los CLIs

## [1.5.0] - 2026-04-29 — Chainlink cross-check + QuantMuse features

### Added
- **`/chainlink` command** + `chainlink-cross-check` skill (4 RPC fallback Ethereum mainnet)
- **`/risk-var`, `/risk-parity`, `/multifactor`** commands (QuantMuse-inspired)
- **Sharpe + Max DD + IC** metrics en `/journal`

## [1.4.0] - 2026-04-28 — FTMO + FundingPips profiles + Localization CR

### Added
- **Profile FTMO** ($10k demo, multi-asset, MT5 EA bridge)
- **Profile fotmarkets** ($30 bonus, MT5 phase-gated)
- **Profile fundingpips** ($10k Zero direct funded)
- **Locale Costa Rica** (UTC-6) — antes era Mexico, mismo offset
- **USD↔CRC** statusline con `fx_rate.sh` cache 1h

## [1.3.0] - 2026-04-23 — Watcher v1 + set-and-forget orders

### Added
- **Watcher daemon** macOS (.app bundle + launchd) — vigila pending_orders.json hourly
- **`pending_lib.py`** CRUD + invalidation + whitelist matrix
- **`/watch`, `/order`, `/sync`** commands

## [1.2.0] - 2026-04-22 — Bookmap + retail strategy v1

### Added
- **Mean Reversion 15m strategy oficial** (Donchian 15 + RSI 35/65 + BB + ATR)
- **Bookmap orderflow** integration (FASE 8.5 morning protocol)
- **Pine Script indicator** (4 filtros automatizados + alertas)

## [1.0.0] - 2026-04-20 — Initial system (retail BingX)

### Added
- Profile retail-bingx ($10 → $13.63 actual)
- 7 agentes especializados (morning-analyst, trade-validator, regime-detector, chart-drafter, risk-manager, journal-keeper, backtest-runner)
- Sistema base: profile.sh, statusline, hooks, MORNING_PROMPT.md
- TradingView MCP integration (78 tools)

---

## Convenciones

- **MAJOR**: cambios breaking en strategy/risk que cambian decisiones de capital real
- **MINOR**: nuevos features (profile, command, skill) sin breaking
- **PATCH**: bugfixes, doc updates, refactors sin afectar trading

Antes de bumpear MAJOR strategy version: backtest re-run debe confirmar el cambio.

## Mantenimiento

Antes de cada release:
1. Re-run pytest suite (`pytest .claude/scripts/tests/`)
2. Re-run backtests si se cambió strategy/risk: `python /tmp/wally_backtest/group_A_btc_meanreversion.py` etc.
3. Update CHANGELOG.md con entries en `[Unreleased]` antes de tag
4. `git tag -a vX.Y.Z -m "..."` + push
