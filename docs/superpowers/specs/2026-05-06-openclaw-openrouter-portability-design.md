# OpenClaw + OpenRouter Portability — Design Spec

**Fecha:** 2026-05-06
**Branch propuesto:** `feature/openclaw-adapter`
**Driver:** Backup/redundancia — el sistema de trading debe correr en OpenClaw como segundo harness, en paridad con Claude Code, para tener independencia de plataforma y resiliencia ante caídas o cambios de pricing.
**Profiles cubiertos en v1:** los 7 (retail, retail-bingx, ftmo, fundingpips, fotmarkets, bitunix, quantfury) — paridad total.

## Contexto previo

- Existe ya un patrón `system/ + adapters/` (spec [2026-04-22-multi-cli-portability-design.md](2026-04-22-multi-cli-portability-design.md)) con adapters funcionales para Claude Code, OpenCode, Codex, Hermes.
- `system/` es la fuente única de verdad (commands/agents/skills/mcp/hooks).
- Cada adapter traduce a su CLI target vía `transform.py`, con git pre-commit hook que regenera automáticamente.
- Esta spec **se alinea con ese patrón**: OpenClaw entra como 5to adapter (mold de Hermes), no como arquitectura separada.

## Decisiones de scope aprobadas

| # | Decisión | Elegido |
|---|---|---|
| 1 | Driver | **Backup/redundancia** (no auto-ingesta Discord, no multi-modelo prioritario) |
| 2 | Ruta | **A — Dual-harness mirror** (CC primario + OC backup) |
| 3 | Profiles | **Los 7** con paridad total |
| 4 | Patrón | **5to adapter** sobre `system/` existente (no arquitectura nueva) |
| 5 | OpenRouter | **Opt-in** vía env var (default Anthropic API directa) |
| 6 | Subagentes en OC | Sin equivalente nativo — proyectados a skills (estilo Hermes) |
| 7 | Hooks (statusline, SessionStart) | NO portados en v1 — evaluar plugin OC en v2 |
| 8 | Estado compartido | Mismos archivos en `.claude/profiles/<name>/memory/` con file locking |
| 9 | Sync de profile activo entre harnesses | NO automático (`WALLY_PROFILE` per-terminal) |

## Architecture

**Principio rector:** una sola fuente de verdad para lógica de trading; harness-specific glue vive en `adapters/`.

```
/Users/josecampos/Documents/wally-trader/
├── system/                                    # YA EXISTE — canonical source
│   ├── commands/  (29 .md)
│   ├── agents/    (12 .md)
│   ├── skills/    (14 dirs en formato agentskills.io)
│   ├── mcp/servers.json                       # MODIFICADO: agrega entry "wally"
│   └── hooks/
│
├── adapters/
│   ├── claude-code/                           # ya existe (symlinks)
│   ├── opencode/                              # ya existe
│   ├── codex/                                 # ya existe (UNTESTED)
│   ├── hermes/                                # ya existe (mold a copiar)
│   └── openclaw/                              # NUEVO
│       ├── install.sh
│       ├── transform.py                       # system/ → .openclaw/
│       ├── test_transform.py
│       └── README.md
│
├── .openclaw/                                 # NUEVO — generado, committed
│   ├── skills/
│   │   ├── wally-agents/<name>/SKILL.md       # 12 skills desde system/agents/
│   │   ├── wally-commands/<name>/SKILL.md     # 29 skills desde system/commands/
│   │   └── wally-skills/  → symlink a ../../system/skills
│   ├── config.json                            # OC config (MCP servers, model, env)
│   └── .gitkeep
│
├── wally-trader-mcp/                          # NUEVO — servidor MCP propio
│   ├── pyproject.toml
│   ├── src/wally_trader_mcp/
│   │   ├── server.py                          # FastMCP entry
│   │   ├── tools/                             # 12 tool modules
│   │   └── __init__.py
│   └── tests/
│
├── shared/wally_core/                         # NUEVO — lib Python compartida
│   ├── pyproject.toml
│   └── src/wally_core/
│       ├── regime.py, validate.py, risk.py, hunt.py,
│       ├── journal.py, signals.py, locking.py,
│       ├── macro.py, ml.py, sentiment.py, multifactor.py
│       └── tests/
│
├── .claude/                                   # Sin cambios
│   ├── commands/  → symlink system/commands
│   ├── agents/    → symlink system/agents
│   ├── scripts/                               # mantienen, importan de wally_core
│   ├── profiles/<name>/memory/                # ESTADO COMPARTIDO (CC + OC)
│   └── settings.json
│
└── tradingview-mcp/                           # YA EXISTE (compartido por todos los adapters)
```

**Tres claves del diseño:**

1. **`adapters/openclaw/` sigue el molde de `adapters/hermes/`.** OpenClaw, igual que Hermes, es una plataforma skills-only sin subagentes nativos. La transformación es: `system/agents/<n>.md → .openclaw/skills/wally-agents/<n>/SKILL.md`, `system/commands/<n>.md → .openclaw/skills/wally-commands/<n>/SKILL.md`, `system/skills/ → .openclaw/skills/wally-skills/` por symlink.

2. **`wally-trader-mcp/` es ortogonal a los adapters.** Es un MCP server independiente que envuelve la lógica crítica. Se registra en `system/mcp/servers.json` (entry nuevo `wally`), y cada `transform.py` de cada adapter lo proyecta al config nativo de su CLI. Resultado: CC, OC, OpenCode, Hermes, Codex todos consumen el mismo MCP.

3. **State compartido en `.claude/profiles/<n>/memory/` no se mueve.** Ambos harnesses leen/escriben los mismos archivos. Concurrencia se resuelve con `filelock` en `wally_core/locking.py` (writes son raros y mayoritariamente append-only).

**Lo que NO se porta a OC en v1:**
- Hooks Claude Code (statusline, SessionStart) — sin equivalente documentado en OC. Evaluar plugin OC en v2.
- Subagentes como concepto independiente — proyectados a skills (sin pérdida funcional, solo cambia orquestación).

## Components

### `wally-trader-mcp/`

Servidor MCP en Python con **FastMCP** (`mcp[cli]>=1.0`). Expone 12 tools agrupadas en 4 dominios:

| Dominio | Tools | Naturaleza |
|---|---|---|
| Análisis | `detect_regime`, `validate_setup`, `multifactor_score`, `ml_score`, `sentiment_score` | Read-only |
| Risk & Sizing | `calculate_risk` (modos: flat-2pct / VaR / parity) | Read-only |
| Workflows activos | `hunt_signals` (bitunix-only), `signal_validate` (bitunix-only), `macross_signal`, `levels_now` | Read + log con lock |
| Estado | `journal_close`, `log_outcome`, `macro_gate_check`, `chainlink_check` | Write con lock |

Convenciones:
- Cada tool toma `profile` como primer argumento (excepto profile-agnostic: `chainlink_check`, `macro_gate_check`).
- Cada tool valida el profile activo antes de ejecutar (rechaza `hunt_signals` si profile ≠ bitunix).
- Output: JSON estructurado siempre. Markdown narrativo se genera en wrappers (skills/CLI), no en el MCP.
- Tests obligatorios: `tests/test_<tool>.py` con golden-file comparing contra outputs de los scripts actuales.

### `shared/wally_core/`

Refactor incremental de scripts en `.claude/scripts/` a una librería importable.

| Módulo | Reemplaza/consolida |
|---|---|
| `regime.py` | `adx_calc.py` + `label_regime` logic |
| `validate.py` | 4-filter check (RSI, BB, Donchian, vela) |
| `risk.py` | flat 2%, VaR (`risk_quant`), Risk Parity (3 modos en una API) |
| `hunt.py` | scoring 0-100 bitunix, ranking |
| `journal.py` | métricas (Sharpe, Max DD, IC, WR, PF) |
| `signals.py` | bitunix log helpers + outcome closure |
| `locking.py` | wrapper `filelock.FileLock` con timeout y stale cleanup |
| `macro.py` | macro_gate + cache refresh + DST |
| `ml.py`, `sentiment.py`, `multifactor.py` | wrappers thin sobre `scripts/ml_system/` |

**Compatibilidad:** scripts existentes en `.claude/scripts/*.py` siguen ejecutables vía bash. Internamente importan de `wally_core`. Cero rotura de skills/commands actuales.

### `adapters/openclaw/` (5to adapter)

Estructura espejo de `adapters/hermes/`:

| Archivo | Función |
|---|---|
| `install.sh` | Crea `.openclaw/`, llama transform.py, instala git hook v1 |
| `transform.py` | `system/` → `.openclaw/skills/` + `.openclaw/config.json` |
| `test_transform.py` | pytest cubriendo translation rules (mismo style que hermes) |
| `README.md` | Setup, troubleshooting, mapping table |

Reglas de translation (basadas en lo verificado en docs.openclaw.ai):

| Source | Destination | Translation |
|---|---|---|
| `system/agents/<n>.md` | `.openclaw/skills/wally-agents/<n>/SKILL.md` | Frontmatter `name`+`description` preservado. `tools: A, B` → `metadata.openclaw.toolsets: [...]` (mapping similar a Hermes). Body con provenance header. |
| `system/commands/<n>.md` | `.openclaw/skills/wally-commands/<n>/SKILL.md` | `description` preservado. `argument-hint` → `<!-- args: ... -->` en body. `allowed-tools` descartado. Filename → skill name → slash trigger. |
| `system/skills/<n>/` | `.openclaw/skills/wally-skills/<n>/` | Symlink (formato agentskills.io ya compatible). Zero transform. |
| `system/mcp/servers.json` | `.openclaw/config.json` (sección `mcp.servers`) | JSON re-mapped al schema OC (igual a CC en estructura, llave `mcp.servers`). |

OpenRouter (opt-in):
- Por defecto `.openclaw/config.json` setea `agents.defaults.model.primary = "anthropic/claude-opus-4-7"` y lee `ANTHROPIC_API_KEY` del env.
- Si `WALLY_USE_OPENROUTER=1` está seteado al correr `install.sh`, el config se genera con `model.primary = "openrouter/auto"` y `OPENROUTER_API_KEY`. Limitación documentada: pierde prompt caching nativo de Anthropic en rutas proxy OpenAI-compat.

### `system/mcp/servers.json` (modificado)

Se agrega entry `wally` (referencia local al MCP propio). Cada adapter ya tiene lógica para proyectar al config nativo de su CLI.

```json
{
  "tradingview": { "command": "node", "args": ["./tradingview-mcp/src/server.js"], "cwd": "<repo>" },
  "wally":       { "command": "python3", "args": ["-m", "wally_trader_mcp"], "cwd": "<repo>" }
}
```

### Build, sync & install (Makefile)

| Comando | Acción |
|---|---|
| `make wally-mcp-install` | `pip install -e wally-trader-mcp/ shared/wally_core/` |
| `make sync-oc` | `bash adapters/openclaw/install.sh` (regenera `.openclaw/`) |
| `make sync-all` | corre install.sh de todos los adapters |
| `make test` | pytest sobre `wally_core/`, `wally-trader-mcp/`, `adapters/*/test_*.py` |
| `make test-parity` | suite de paridad CC↔OC (lenta, nightly) |
| `make doctor` | health check: deps Python, MCP servers up, locks libres, profile válido |

### Esfuerzo estimado

| Componente | Esfuerzo |
|---|---|
| `wally-trader-mcp/` esqueleto + 12 tools + tests | ~2 semanas |
| `shared/wally_core/` refactor sin rotura | ~1 semana |
| `adapters/openclaw/` (mold de hermes) | ~3 días |
| OC settings + Makefile + doctor | ~1 día |
| Tests de paridad CC↔OC + e2e | ~3 días |
| **Total v1** | **~3-4 semanas parciales** |

## Data Flow

### Read path (sin riesgo)

Caso típico: usuario corre `/morning` en OC.

```
1. OC user input: "/morning"
2. OC carga skill .openclaw/skills/wally-commands/morning/SKILL.md
3. Skill instruye al LLM:
   - leer .claude/profiles/<active>/config.md
   - llamar mcp__wally__detect_regime(profile=active)
   - llamar mcp__wally__macro_gate_check()
   - llamar mcp__wally__sentiment_score()
   - llamar mcp__tradingview__quote_get(symbol=...)
4. wally-trader-mcp ejecuta lógica desde shared/wally_core/
5. Resultado JSON → LLM sintetiza → reporte markdown al usuario
```

CC ejecuta exactamente la misma cadena. Cero divergencia funcional porque ambos llaman al mismo MCP con la misma lógica.

### Write path (con locking)

Solo 4 archivos son writeable y compartidos:

| Archivo | Frecuencia write | Estrategia |
|---|---|---|
| `signals_received.md` (bitunix) | Por cada `/signal` y `/punk-hunt` aprobado | append-only + flock |
| `signals_received.csv` (bitunix) | Idem | append-only + flock |
| `trading_log.md` (todos los profiles) | Al cierre de día via `/journal` | rewrite atómico (temp+rename) + flock |
| `equity_curve.csv` (todos) | Idem | append-only + flock |

Regla: todo write a esos archivos pasa por `wally_core/locking.shared_write`:

```python
from wally_core.locking import shared_write
with shared_write(profile, "signals_received.csv") as f:
    f.write(row)
```

Internamente `filelock.FileLock` con timeout 5s, retry 3 veces, cleanup de locks huérfanos (PID inexistente).

### Conflictos cross-harness

Decisión consciente: **NO sincronizamos profile activo entre harnesses**. Cada terminal mantiene su propio `WALLY_PROFILE`. Statusline en CC y `openclaw status` en OC dejan claro qué profile cada uno está mirando. Razón: sync automático introduce bugs sutiles cuando el usuario cambia profile mid-trade.

| Situación | Comportamiento |
|---|---|
| Ambos leen estado | OK, sin conflicto |
| OC ejecuta `/signal` → escribe a CSV | CC ve el cambio en su próxima lectura |
| CC y OC escriben simultáneo al CSV | filelock serializa, ambas escrituras se persisten |
| Profile mismatch entre terminales | Usuario lo nota visualmente; no hay corrección automática |

### Health & telemetry

`wally_core/health.py` chequea al inicio de critical paths:

- `mcp__wally__ping()` con timeout 2s
- `mcp__tradingview__tv_health_check()`
- Profile válido (lee `WALLY_PROFILE`)
- Macro cache fresh (<24h)
- Filelocks libres (no stale)

CC ya tiene esto parcial; OC lo invoca desde un skill `/doctor`.

## Error Handling

### Modos de falla y respuestas

| Falla | Detección | Respuesta | Recuperación |
|---|---|---|---|
| `wally-trader-mcp` no responde | Health check o timeout 5s | Skills caen a fallback bash (`python3 -m wally_core.<module> --json`). El cerebro sigue accesible | Auto-reintento al próximo call |
| TradingView MCP cae | `tv_health_check()` falla | NO operar nuevos trades. Workflows read-only siguen | Manual: `tv_launch` |
| Anthropic API down (CC) | SDK error | OC sigue funcionando. Si OC también usa Anthropic → fallback OpenRouter si `WALLY_USE_OPENROUTER=1` | Sin acción |
| Filelock timeout 5s | Otro proceso writing >5s | Error claro: "concurrent write detected, retry". Reintento manual | Manual |
| Stale lock (.lock con PID muerto) | Auto-detectado en `locking.py` (age >60s + PID gone) | Auto-cleanup antes de reintentar | Auto |
| Profile inválido | Validation entry de cualquier tool | Error: "profile foo not found". Aborta | Manual |
| Macro cache stale (>24h) | Health check | Auto-refresh si online; warning si offline | Auto/manual |
| MT5 bridge down (ftmo/fundingpips) | Guardian script falla | NO permitir nuevos trades en esos profiles. Otros profiles siguen | Manual: relaunch EA |
| `signals_received.csv` schema drift | Schema check al write | Aborta + log a `bitunix_log_errors.log`. **No corrompe el CSV.** | Manual: revisar log |
| Conflicto profile entre CC y OC | Statusline visible en cada terminal | El usuario lo nota visualmente | Manual |
| `wally_core` import fail | ImportError al lanzar MCP | MCP no arranca → fallback bash o "MCP unavailable" | `make doctor` |

### Principios

1. **Boundaries explícitos.** Validación solo en tool entry points y al leer archivos del usuario. Lógica interna confía en sus inputs (matchea regla de CLAUDE.md "no defensive validation for impossible scenarios").
2. **Fallar ruidoso.** Errores con stack trace al usuario. Nunca `try: ... except: pass`. Excepción: filelock retry interno con cap.
3. **Estado nunca inconsistente.** Writes append-only o atómicos (temp+rename). Schema drift → abort antes de escribir.
4. **Health check antes de critical paths.** `signal_validate`, `journal_close`, `hunt_signals` corren `health_check()` first.
5. **Fallback bash es contrato.** wally-trader-mcp es opcional para correctness; obligatorio solo para latencia/UX. Skills tienen instrucción explícita de fallback.

### Recovery scenarios documentados

- **A: usuario cierra OC mid-write a CSV.** Proceso muere → filelock libera (atexit del SO). Si lock huérfano queda: próximo write detecta PID muerto y limpia. Buffer flush antes de release garantiza consistencia.
- **B: CC y OC corren `/journal` simultáneo.** filelock serializa: uno gana, otro espera. Ambos persisten. Si esperan >5s, segundo ve error claro.
- **C: wally-trader-mcp se reinicia mid-sesión.** Tool call falla → skill cae a fallback bash. Próximo call re-conecta. **MCP es stateless** — restart siempre seguro.
- **D: Anthropic rate-limit en CC.** Si comparte key con OC, ambos esperan. Mitigación: keys separadas.

### Logging

Errores van a logs versionados por día:

```
logs/<YYYY-MM-DD>/
├── wally-mcp.log         # stdout/stderr del MCP
├── cc-skills.log         # skills CC con errores
├── oc-skills.log         # skills OC con errores
├── locking.log           # filelock contention events
└── bitunix_log_errors.log # schema drift de CSV
```

Rotación: `logrotate` 30 días retention. No commitea al repo.

## Testing

### Pirámide

```
                  ┌──────────────────┐
                  │ E2E paridad CC↔OC│  ~5 tests, lentos, manual+nightly
                  └──────────────────┘
                ┌──────────────────────┐
                │ Integration MCP+state│  ~30 tests, CI cada PR
                └──────────────────────┘
              ┌──────────────────────────┐
              │ Unit wally_core/* + locks│  ~150 tests, CI cada commit
              └──────────────────────────┘
```

### Unit (`shared/wally_core/tests/`)

Cobertura mínima por módulo:

| Módulo | Cobertura | Casos críticos |
|---|---|---|
| `regime.py` | 90% | RANGE/TRENDING/VOLATILE labels + ADX edges (20, 25, 40) |
| `validate.py` | 95% | 4-filter LONG, 4-filter SHORT, NO-GO si falla cada filtro individual |
| `risk.py` | 95% | flat 2%, VaR, parity, leverage caps por profile (10x retail, 20x bitunix) |
| `hunt.py` | 85% | scoring 0-100, top-pick, filtro tier-0 |
| `journal.py` | 90% | Sharpe, Max DD, IC sobre fixtures conocidas |
| `signals.py` | 95% | append + schema validation + outcome closure |
| `locking.py` | 100% | timeout, stale cleanup, retry behavior |
| `macro.py` | 80% | event windows, DST, cache freshness |

Framework: pytest. Fixtures en JSON para OHLCV. Sin mocks de Binance/TV — snapshots del histórico.
Comando: `make test-unit` → < 30s.

### Integration (`wally-trader-mcp/tests/`)

| Test | Qué valida |
|---|---|
| `test_mcp_handshake.py` | Server arranca + responde a `initialize` |
| `test_tool_<name>.py` (×12) | Cada tool: input válido → output JSON shape esperada |
| `test_concurrent_writes.py` | 5 procesos paralelos a `signals_received.csv` → 5 filas, sin corrupción |
| `test_fallback_bash.py` | Apaga MCP → `python3 -m wally_core.regime` da output equivalente |
| `test_profile_isolation.py` | profile=bitunix no puede leer/escribir memory de profile=ftmo |
| `test_health_check.py` | health detecta TV down, MCP down, profile inválido, cache stale |

Framework: pytest + mcp Python SDK como cliente. Subprocess management para arrancar/matar server.
Comando: `make test-integration` → ~2min.

### Adapter transform (`adapters/openclaw/test_transform.py`)

Mismo molde que `adapters/hermes/test_transform.py`. Cubre:
- agent → skill frontmatter (basic, MCP toolset, web toolset, subagents toolset, no-tools default)
- agent body preservation con provenance header
- command → skill (basic, argument-hint, slash naming, no-frontmatter)
- clean_group (orphan removal, missing-dir no-op)
- MCP entry projection a `.openclaw/config.json`
- OpenRouter opt-in flag (`WALLY_USE_OPENROUTER=1`) genera config diferente

### Paridad CC ↔ OC (clave del proyecto)

Suite `tests/parity/`:

| Test | Workflow | Comparación |
|---|---|---|
| `parity_morning.sh` | `/morning` profile bitunix sobre snapshot fixture | Diff de reportes (estructura, no texto exacto) |
| `parity_punk_hunt.sh` | `/punk-hunt` sobre fixture mercado congelado | Top pick + score matchean ±0 |
| `parity_validate.sh` | `/validate` setup específico | GO/NO-GO + razón matchean exact |
| `parity_risk.sh` | `/risk` 5 escenarios (flat, VaR, parity, leverage caps) | Position size matchea ±$0.01 |
| `parity_journal.sh` | `/journal` con trade log fixture | Métricas Sharpe/WR/PF ±0.001 |
| `parity_signal.sh` | `/signal BTCUSDT LONG ...` con fixture | Score + GO/NO-GO matchean exact |

Mecánica:
1. Test arranca CC en non-interactive mode con prompt fijo
2. Captura output JSON estructurado
3. Repite con OC (`openclaw agent --message`)
4. `diff` ignorando timestamps/UUIDs

**No comparamos:** redacción narrativa del LLM (varía entre runs).
**Sí comparamos:** cálculos, decisiones GO/NO-GO, estructura del output, side-effects en files compartidos.

Comando: `make test-parity` → ~10 min. Nightly cron, no en cada PR.

### E2E (manual + scripted)

5 escenarios completos:

1. **Morning session bitunix:** abrir CC → `/punk-morning` → output esperado. Repetir en OC. Resultados equivalentes.
2. **Live signal validate:** simular signal Discord → `/signal BTC LONG ...` → auto-log en `signals_received.csv` → verificar misma fila desde el otro harness.
3. **End-of-day journal:** `/journal` con día sintético → métricas correctas + equity_curve actualizada.
4. **Concurrent writes:** CC y OC simultáneo, `/signal` casi al mismo tiempo desde ambos → CSV con ambas filas, sin corrupción.
5. **Fallback path:** matar `wally-trader-mcp` mid-sesión → skills caen a bash sin error visible al usuario.

Documentados en `tests/e2e/scenarios.md`. Manual cada release menor.

### CI matrix

| Trigger | Tests | Duración |
|---|---|---|
| Cada commit feature branch | unit | <30s |
| Cada PR | unit + integration + lint + adapter transform | ~3min |
| Merge a main | unit + integration + paridad | ~13min |
| Nightly cron | todo + e2e scripted (1, 2, 3) | ~30min |
| Pre-release | e2e completo + manual scenarios 4, 5 | ~1h |

Plataforma: GitHub Actions (si repo en GH) o `scripts/ci_local.sh`.

### Validación operativa post-deploy

Antes de declarar v1 completo:

- [ ] 7 días corriendo CC + OC en paralelo, mismo profile bitunix, sin discrepancias en `signals_received.csv`
- [ ] Al menos 1 trade real ejecutado vía workflow OC
- [ ] `make doctor` verde en ambas instalaciones
- [ ] Documentación `docs/openclaw-setup.md` validada por alguien externo (un amigo que lo siga step-by-step)

## OpenRouter (opt-in)

OpenRouter es **provider de modelos dentro de OpenClaw**, no integración separada con Claude Code. CC usa el SDK propietario de Anthropic y no se puede redirigir su endpoint sin parchear el binario.

Casos de uso para opt-in:
- A/B test de modelos (Kimi, GPT-5, Gemini, Llama) para tareas específicas (ej. ML feature extraction)
- Acceso a modelos no-Anthropic sin manejar múltiples API keys

Activación:
```bash
WALLY_USE_OPENROUTER=1 bash adapters/openclaw/install.sh
```

Genera `.openclaw/config.json` con:
```json5
{
  env: { OPENROUTER_API_KEY: "$OPENROUTER_API_KEY" },
  agents: { defaults: { model: { primary: "openrouter/auto" } } }
}
```

Limitaciones documentadas:
- Pierde prompt caching nativo de Anthropic en rutas proxy OpenAI-compat
- `serviceTier` y otras features Anthropic-specific no se reenvían

Default (sin opt-in): Anthropic API directa, mejor performance, mismo modelo que CC.

## Decisiones No-Goals

- **NO sync automático de profile entre CC y OC.** El usuario maneja `WALLY_PROFILE` per-terminal explícitamente.
- **NO porting de hooks (statusline, SessionStart) en v1.** Sin equivalente documentado en OC. Reevaluar v2 si es necesario un plugin OC.
- **NO duplicación de wally_core en otro lenguaje.** Python es el target único. Si OC plugin requiere TS/JS, hace shell-out al MCP.
- **NO auto-ingesta de canales (Discord/Telegram/etc.).** Aunque OC soporta 30+ canales, este caso de uso queda fuera de v1 (driver es backup, no automation).
- **NO sustitución de Claude Code.** OC es backup; CC primary. Cualquier feature que solo exista en CC queda OK por ahora.

## Riesgos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Schema OpenClaw cambia mid-desarrollo | Media | Alto (refactor adapter) | Pin de versión en install.sh; revisar release notes mensual |
| Filelock contention bajo concurrencia alta | Baja | Bajo (writes raros) | Timeout 5s + retry; logging de events |
| `wally-trader-mcp` introduces bugs no presentes en scripts originales | Media | Alto (paridad rota) | Golden-file tests por tool; fallback bash siempre disponible |
| `wally_core` refactor rompe scripts existentes | Media | Medio | CI corre tests sobre scripts antes y después; rollout gradual módulo por módulo |
| OpenRouter caching loss reduce calidad | Baja | Bajo | Opt-in only; default Anthropic API directa |
| MCP servers no arrancan en clean install | Media | Alto | `make doctor` cubre; install.sh valida deps |

## Implementación: orden de fases

Las fases son secuenciales — cada una bloquea a la siguiente.

1. **Fase 1 (semana 1):** `shared/wally_core/` esqueleto + módulos puros (regime, validate, risk, locking, journal, signals). Tests unit. Cero cambio en scripts existentes.
2. **Fase 2 (semana 2):** `wally-trader-mcp/` con primeras 6 tools (read-only). Tests integration. Skills CC siguen sin tocar.
3. **Fase 3 (semana 2-3):** `wally-trader-mcp/` completo (12 tools). Refactor scripts críticos para usar `wally_core`. Tests paridad CC contra scripts pre-refactor.
4. **Fase 4 (semana 3):** `adapters/openclaw/` (mold de hermes) + `.openclaw/` config. Install.sh, transform.py, tests.
5. **Fase 5 (semana 3-4):** Tests paridad CC↔OC. E2E scripted. Validación operativa 7 días.
6. **Fase 6 (release):** docs/openclaw-setup.md + `make doctor` verde + merge a main.

## Apéndices

### A. Mapping tools wally-trader-mcp ↔ scripts existentes

| Tool MCP | Script actual reemplazado |
|---|---|
| `detect_regime` | `.claude/scripts/adx_calc.py` + lógica regime-detector agent |
| `validate_setup` | trade-validator agent + `validate.py` (nuevo) |
| `calculate_risk` | risk-manager agent + `.claude/scripts/risk_quant.py` |
| `hunt_signals` | punk-hunt-analyst + `.claude/scripts/punk_hunt_*.py` |
| `signal_validate` | signal-validator agent + `.claude/scripts/bitunix_log.py` |
| `journal_close` | journal-keeper + `.claude/scripts/journal_metrics.py` |
| `log_outcome` | `.claude/scripts/bitunix_log_outcome.py` |
| `macro_gate_check` | `.claude/scripts/macro_gate.py` |
| `chainlink_check` | `.claude/scripts/chainlink_price.sh` |
| `ml_score` | ml-analyst + `scripts/ml_system/predict.py` |
| `multifactor_score` | `.claude/scripts/multifactor.py` |
| `sentiment_score` | sentiment-analyst + `scripts/ml_system/sentiment.py` |

### B. Comandos de uso final

Setup primera vez (post-merge):
```bash
make wally-mcp-install
bash adapters/openclaw/install.sh
make doctor
```

Día a día (sin cambios para CC):
```bash
# Edits canónicos:
$EDITOR system/commands/morning.md  # CC ve cambio inmediato
git commit -am "fix morning"        # pre-commit hook regenera .openclaw/, .opencode/, .hermes/
```

OpenClaw uso:
```bash
openclaw agent --message "/morning"
openclaw mcp list   # ver MCP servers conectados
openclaw skills list  # ver wally-agents/, wally-commands/, wally-skills/
```

### C. Referencias

- Spec previa: `docs/superpowers/specs/2026-04-22-multi-cli-portability-design.md`
- OpenClaw docs: https://docs.openclaw.ai
- OpenClaw skills format: https://docs.openclaw.ai/tools/creating-skills.md
- OpenClaw MCP: https://docs.openclaw.ai/cli/mcp.md
- OpenClaw OpenRouter: https://docs.openclaw.ai/providers/openrouter.md
- agentskills.io standard (formato shared con Hermes): mismo schema que `system/skills/`
