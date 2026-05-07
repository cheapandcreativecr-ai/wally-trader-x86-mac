# OpenClaw + OpenRouter + Notion Memory Portability — Design Spec

**Fecha:** 2026-05-06
**Branch propuesto:** `feature/openclaw-adapter`
**Driver primario:** Backup/redundancia — el sistema de trading debe correr en OpenClaw como segundo harness, en paridad con Claude Code, para tener independencia de plataforma.
**Driver secundario:** Cross-harness/cross-device memory unification vía Notion MCP — abrir CC en la mañana → registrar entries → continuar análisis y vigilancia desde OC en otra terminal/máquina viendo el mismo estado en tiempo real.
**Multi-tenancy:** El hermano del usuario instalará la misma codebase. Cada usuario apunta a su propio Notion workspace vía su `NOTION_API_KEY` — aislamiento automático, cero código nuevo.
**Profiles cubiertos en v1:** los 7 (retail, retail-bingx, ftmo, fundingpips, fotmarkets, bitunix, quantfury) — paridad total.

## Contexto previo

- Existe ya un patrón `system/ + adapters/` (spec [2026-04-22-multi-cli-portability-design.md](2026-04-22-multi-cli-portability-design.md)) con adapters funcionales para Claude Code, OpenCode, Codex, Hermes.
- `system/` es la fuente única de verdad (commands/agents/skills/mcp/hooks).
- Cada adapter traduce a su CLI target vía `transform.py`, con git pre-commit hook que regenera automáticamente.
- Esta spec se alinea con ese patrón: **OpenClaw entra como 5to adapter** (mold de Hermes), no como arquitectura separada.

## Decisiones de scope aprobadas

| # | Decisión | Elegido |
|---|---|---|
| 1 | Driver | **Backup/redundancia** + **memory unification cross-harness** |
| 2 | Ruta | **A — Dual-harness mirror** (CC primario + OC backup) |
| 3 | Profiles | **Los 7** con paridad total |
| 4 | Patrón | **5to adapter** sobre `system/` existente (no arquitectura nueva) |
| 5 | OpenRouter | **Opt-in** vía env var (default Anthropic API directa) |
| 6 | Subagentes en OC | Sin equivalente nativo — proyectados a skills (estilo Hermes) |
| 7 | Hooks (statusline, SessionStart) | NO portados en v1 — evaluar plugin OC en v2 |
| 8 | Sync de profile activo entre harnesses | NO automático (`WALLY_PROFILE` per-terminal) |
| 9 | **Memoria** | **Abstracción con 3 backends: local / notion / hybrid (default)** |
| 10 | **Multi-tenant (hermano)** | **Workspaces Notion separados por `NOTION_API_KEY`** — no shared data, no read-only sharing en v1 |
| 11 | Backend default v1 | **`hybrid`** — local primary + Notion async mirror |

## Architecture

**Principio rector:** una sola fuente de verdad para lógica de trading; harness-specific glue vive en `adapters/`; **memoria es interfaz con backends intercambiables**.

```
/Users/josecampos/Documents/wally-trader/
├── system/                                    # YA EXISTE — canonical source
│   ├── commands/, agents/, skills/, hooks/
│   └── mcp/servers.json                       # MODIFICADO: agrega "wally" + "notion"
│
├── adapters/
│   ├── claude-code/, opencode/, codex/, hermes/   # ya existen
│   └── openclaw/                              # NUEVO (mold de hermes)
│       ├── install.sh, transform.py, test_transform.py, README.md
│
├── .openclaw/                                 # NUEVO — generado, committed
│   ├── skills/{wally-agents,wally-commands,wally-skills}/
│   └── config.json                            # MCP servers + model + env
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
│       ├── macro.py, ml.py, sentiment.py, multifactor.py,
│       ├── memory/                            # NUEVO — storage abstraction
│       │   ├── __init__.py                    # get_backend(profile) factory
│       │   ├── interface.py                   # MemoryBackend ABC
│       │   ├── local.py                       # LocalBackend (filesystem + flock)
│       │   ├── notion.py                      # NotionBackend (Notion MCP client)
│       │   ├── hybrid.py                      # HybridBackend (local + async Notion)
│       │   ├── schemas.py                     # DB schemas (Pydantic models)
│       │   └── migrate.py                     # CSV → Notion one-time migration
│       └── tests/
│
├── .claude/                                   # Sin cambios estructurales
│   ├── commands/, agents/   → symlinks a system/
│   ├── scripts/                               # mantienen, importan de wally_core
│   ├── profiles/<name>/                       # ESTADO LOCAL (cache si backend=hybrid)
│   │   ├── config.md                          # +seccion memory.backend, memory.notion
│   │   └── memory/                            # archivos locales (cache o source si backend=local)
│   └── settings.json
│
└── tradingview-mcp/                           # YA EXISTE
```

**Cuatro claves del diseño:**

1. **`adapters/openclaw/` sigue el molde de `adapters/hermes/`.** OpenClaw es plataforma skills-only sin subagentes nativos. La transformación es: `system/agents/<n>.md → .openclaw/skills/wally-agents/<n>/SKILL.md`, `system/commands/<n>.md → .openclaw/skills/wally-commands/<n>/SKILL.md`, `system/skills/ → .openclaw/skills/wally-skills/` por symlink.

2. **`wally-trader-mcp/` es ortogonal a los adapters.** Es un MCP server independiente que envuelve la lógica crítica. Se registra en `system/mcp/servers.json` (entry `wally`), y cada `transform.py` lo proyecta al config nativo de su CLI. CC, OC, OpenCode, Hermes, Codex consumen el mismo MCP.

3. **Memoria es interfaz con 3 backends** — `LocalBackend`, `NotionBackend`, `HybridBackend`. Las tools de `wally-trader-mcp` que escriben (`signal_validate`, `journal_close`, `log_outcome`) llaman a `memory.get_backend(profile).append_X(...)`. El backend lo decide la config del profile. **Default v1: `hybrid`** (local primary, Notion async mirror) — gives instant local UX + cross-device sync sin bloqueos.

4. **Multi-tenancy automática vía Notion API keys separadas.** El hermano del usuario corre el mismo código en su Mac, con su propio `NOTION_API_KEY` apuntando a su Notion workspace. Cero código nuevo para soportarlo. Aislamiento es server-side de Notion.

**Lo que NO se porta a OC en v1:**
- Hooks Claude Code (statusline, SessionStart) — sin equivalente documentado en OC.
- Subagentes como concepto independiente — proyectados a skills (sin pérdida funcional).

**No-goals explícitos:**
- NO sync automático de profile entre CC y OC (cada terminal mantiene su `WALLY_PROFILE`).
- NO read-only sharing entre brothers (cada workspace Notion es privado de su dueño).
- NO offline-only mode default (backend `hybrid` requiere conexión para mirror; se degrada a local-only si Notion cae).
- NO migración automática del histórico al cambiar de backend (script `migrate.py` se corre manualmente).

## Memory Layer

### Esquema Notion (auto-creado por `migrate.py` si no existe)

Workspace structure por usuario:

```
Wally Trader (workspace)
├── 📊 Profiles                (DB) — config snapshot por profile
│   └── cols: name, capital_usd, capital_btc, strategy, window_cr, last_updated
├── 📈 Trades Log              (DB) — reemplaza trading_log.md (estructurado)
│   └── cols: id (UUID), profile, date, asset, side, entry, sl, tp1, tp2, tp3,
│             leverage, position_size_usd, exit_price, pnl_usd, pnl_pct, R,
│             status (open|tp1_hit|tp2_hit|tp3_hit|sl|closed_manual),
│             notes (rich text), source (manual|signal|hunt|copy)
├── 📡 Signals Received        (DB) — reemplaza signals_received.csv/md
│   └── cols: id (UUID), ts, profile, source (discord|punk-hunt|self),
│             symbol, side, entry, sl, tp1, tp2, tp3, leverage, score,
│             decision (GO|NO-GO|WARN), outcome (TP1|TP2|TP3|SL|manual|pending),
│             exit_price, pnl_usd, raw_message (rich text)
├── 💰 Equity Curve            (DB) — reemplaza equity_curve.csv
│   └── cols: profile, date, equity_usd, equity_btc, daily_pnl_usd, daily_return_pct
├── 📔 Daily Journal           (DB-pages) — narrative end-of-day por profile
│   └── cols: profile, date, summary, lessons, screenshots (files)
└── 📅 Weekly Digest           (DB-pages) — auto-generadas domingo
    └── cols: week, summary, highlights, macro_events_next_week
```

**Diseño consciente:** todos son DBs (no pages individuales) → permiten queries, filtros, vistas custom desde la UI de Notion. El usuario puede armar dashboards en Notion (kanban de signals, calendar de trades) sin tocar código.

### `MemoryBackend` interface

```python
# wally_core/memory/interface.py
from abc import ABC, abstractmethod
from typing import Iterable
from .schemas import Trade, Signal, EquityRow, JournalEntry

class MemoryBackend(ABC):
    @abstractmethod
    def append_signal(self, profile: str, signal: Signal) -> str: ...  # returns UUID
    @abstractmethod
    def update_signal_outcome(self, signal_id: str, outcome: str, exit_price: float, pnl_usd: float) -> None: ...
    @abstractmethod
    def read_signals(self, profile: str, *, since: date | None = None, status: str | None = None) -> Iterable[Signal]: ...
    @abstractmethod
    def append_trade(self, profile: str, trade: Trade) -> str: ...
    @abstractmethod
    def append_equity(self, profile: str, row: EquityRow) -> None: ...
    @abstractmethod
    def append_journal(self, profile: str, entry: JournalEntry) -> None: ...
    @abstractmethod
    def health_check(self) -> dict: ...  # backend-specific status
```

### `LocalBackend`

- Reads/writes `.claude/profiles/<name>/memory/{signals_received.csv, signals_received.md, trading_log.md, equity_curve.csv, daily_journal/<date>.md}`
- Wraps writes con `filelock.FileLock` (5s timeout, stale cleanup)
- UUIDs locales generados con `uuid.uuid4()`
- Esquema enforcement vía Pydantic (Signal, Trade) antes de write

### `NotionBackend`

- Cliente del MCP server `notion` (registrado en `system/mcp/servers.json`)
- Cada `append_X` → MCP tool call (e.g., `notion.create_page` con properties tipadas)
- Cada `read_X` → `notion.query_database` con filtros
- UUIDs son los `page_id` de Notion (estables, queryable cross-device)
- Cache local opcional para reads (configurable, default off en notion-only)
- Maneja rate limits con exponential backoff (3 retries, 1s/2s/4s)
- Health check pinguea workspace y verifica DBs existen

### `HybridBackend` (default v1)

- Write path: write a local SYNC primero (UX instant) → schedule async write a Notion (background thread / task queue)
- Read path: read local PRIMERO (fast); si stale (>5min) o explícito refresh, sync desde Notion
- Conflict resolution: **local wins** durante sesión activa; al final de sesión `journal_close` triggers full sync local → Notion (truth = local at session end)
- Si Notion API down: writes locales OK, queue de pending Notion writes en `.claude/profiles/<name>/memory/.notion_pending.jsonl`. Próximo health_check con conexión drena la queue.

**Razón para hybrid default:** elimina el trade-off latencia vs sync. Local da UX instant, Notion da cross-device. Falla del API de Notion no rompe la sesión activa.

### Profile config (formato)

`.claude/profiles/<name>/config.md` gana sección:

```yaml
memory:
  backend: hybrid              # local | notion | hybrid
  notion:
    workspace: "Wally Trader"  # nombre human-readable, opcional
    databases:                 # IDs poblados por migrate.py
      profiles: ""             # vacío = auto-crear/discover
      trades_log: ""
      signals_received: ""
      equity_curve: ""
      daily_journal: ""
      weekly_digest: ""
    sync_interval_sec: 30      # cada cuánto el async drains queue (hybrid only)
    rate_limit_rps: 3          # Notion API limit ~3 req/s
```

`NOTION_API_KEY` se lee del env (no se commitea).

### Migration script (`memory/migrate.py`)

Comando: `python -m wally_core.memory.migrate --profile bitunix --dry-run`

Flujo:
1. Lee `signals_received.csv`, `trading_log.md`, `equity_curve.csv` del profile
2. Si `notion.databases.signals_received` está vacío → crea las DBs en Notion vía MCP
3. Genera UUIDs para rows existentes (preserva timestamps)
4. Bulk-inserts via Notion MCP (chunks de 100, respeta rate limits)
5. Escribe IDs de DB de vuelta a `config.md`
6. Verifica counts: local rows == notion rows
7. Switch backend de `local` → `hybrid` en config.md (manual confirmation)

Reversible: `migrate.py --rollback` exporta Notion → CSV y restaura backend a `local`.

**Idempotente:** corre 2 veces sin re-insertar (chequea UUID existence en Notion before insert).

## Components

### `wally-trader-mcp/`

Servidor MCP en Python con **FastMCP** (`mcp[cli]>=1.0`). 12 tools en 4 dominios:

| Dominio | Tools | Naturaleza |
|---|---|---|
| Análisis | `detect_regime`, `validate_setup`, `multifactor_score`, `ml_score`, `sentiment_score` | Read-only |
| Risk & Sizing | `calculate_risk` (modos: flat-2pct / VaR / parity) | Read-only |
| Workflows activos | `hunt_signals` (bitunix-only), `signal_validate` (bitunix-only), `macross_signal`, `levels_now` | Read + log via memory backend |
| Estado | `journal_close`, `log_outcome`, `macro_gate_check`, `chainlink_check` | Write via memory backend |

Convenciones:
- Cada tool toma `profile` como primer arg (excepto profile-agnostic).
- Tools que escriben usan `memory.get_backend(profile)` — agnostic del backend concreto.
- Output: JSON estructurado siempre. Markdown narrativo en wrappers (skills/CLI).
- Tests: golden-file per tool comparando contra outputs scripts actuales.

### `shared/wally_core/`

| Módulo | Reemplaza/consolida |
|---|---|
| `regime.py` | `adx_calc.py` + `label_regime` |
| `validate.py` | 4-filter check (RSI, BB, Donchian, vela) |
| `risk.py` | flat 2%, VaR, Risk Parity (3 modos) |
| `hunt.py` | scoring 0-100 bitunix, ranking |
| `journal.py` | métricas (Sharpe, Max DD, IC, WR, PF) |
| `signals.py` | bitunix log helpers (delegating to memory backend) |
| `locking.py` | wrapper `filelock.FileLock` (usado solo por `LocalBackend`) |
| `macro.py` | macro_gate + cache + DST |
| `ml.py`, `sentiment.py`, `multifactor.py` | wrappers thin sobre `scripts/ml_system/` |
| `memory/` | abstraction layer (interface + 3 backends + schemas + migrate) |

**Compatibilidad:** scripts existentes en `.claude/scripts/*.py` siguen ejecutables vía bash. Internamente importan de `wally_core`. Cero rotura.

### `adapters/openclaw/`

Estructura espejo de `adapters/hermes/`:

| Archivo | Función |
|---|---|
| `install.sh` | Crea `.openclaw/`, llama transform.py, instala git hook v1 |
| `transform.py` | `system/` → `.openclaw/skills/` + `.openclaw/config.json` |
| `test_transform.py` | pytest cubriendo translation rules (mismo style que hermes) |
| `README.md` | Setup, troubleshooting, mapping table |

Translation rules (basadas en docs.openclaw.ai):

| Source | Destination | Translation |
|---|---|---|
| `system/agents/<n>.md` | `.openclaw/skills/wally-agents/<n>/SKILL.md` | `name`+`description` preservado. `tools: A, B` → `metadata.openclaw.toolsets: [...]` (mapping similar a Hermes — verificar field name exacto en Fase 4). Body con provenance header. |
| `system/commands/<n>.md` | `.openclaw/skills/wally-commands/<n>/SKILL.md` | `description` preservado. `argument-hint` → `<!-- args: ... -->` en body. `allowed-tools` descartado. Filename → slash trigger. |
| `system/skills/<n>/` | `.openclaw/skills/wally-skills/<n>/` | Symlink. Zero transform (formato agentskills.io ya compatible). |
| `system/mcp/servers.json` | `.openclaw/config.json` (sección `mcp.servers`) | JSON re-mapped al schema OC (igual a CC en estructura). |

OpenRouter (opt-in):
- Default: `model.primary = "anthropic/claude-opus-4-7"` con `ANTHROPIC_API_KEY`
- `WALLY_USE_OPENROUTER=1` al correr `install.sh`: `model.primary = "openrouter/auto"` con `OPENROUTER_API_KEY`. Limitación: pierde prompt caching nativo.

### `system/mcp/servers.json` (modificado)

```json
{
  "tradingview": { "command": "node", "args": ["./tradingview-mcp/src/server.js"], "cwd": "<repo>" },
  "wally":       { "command": "python3", "args": ["-m", "wally_trader_mcp"], "cwd": "<repo>" },
  "notion":      { "command": "npx", "args": ["-y", "@notionhq/notion-mcp-server"], "env": { "NOTION_API_KEY": "${NOTION_API_KEY}" } }
}
```

Adapter de Notion MCP a verificar en Fase 1 — si el oficial `@notionhq/notion-mcp-server` no encaja, alternativas: `@suekou/mcp-notion-server` o cliente Python custom thin sobre `notion-client` SDK.

### Build, sync & install (Makefile)

| Comando | Acción |
|---|---|
| `make wally-mcp-install` | `pip install -e wally-trader-mcp/ shared/wally_core/` |
| `make sync-oc` | `bash adapters/openclaw/install.sh` |
| `make sync-all` | corre install.sh de todos los adapters |
| `make notion-init` | guía interactiva para setup Notion (API key, workspace, run migrate.py) |
| `make notion-migrate PROFILE=<name>` | migrate CSVs locales → Notion DBs (idempotente) |
| `make notion-rollback PROFILE=<name>` | export Notion → CSV + switch backend a `local` |
| `make test` | pytest sobre todo |
| `make test-parity` | suite paridad CC↔OC (lenta, nightly) |
| `make doctor` | health check: deps, MCP servers, locks, profile, backend memory, Notion API |

### Esfuerzo estimado v1

| Componente | Esfuerzo |
|---|---|
| `shared/wally_core/` core modules (regime, validate, risk, etc.) | 1 sem |
| `shared/wally_core/memory/` (interface + 3 backends + migrate + tests) | 1.5 sem |
| `wally-trader-mcp/` esqueleto + 12 tools + tests | 2 sem |
| `adapters/openclaw/` (mold de hermes) | 3 días |
| Notion DBs schema + migration tooling | 3 días |
| OC settings + Makefile + doctor + notion-init | 2 días |
| Tests paridad CC↔OC + e2e + Notion sandbox | 4 días |
| **Total v1** | **~5 semanas parciales** |

## Data Flow

### Read path (sin riesgo)

Caso típico: usuario corre `/morning` en OC.

```
1. OC user input: "/morning"
2. OC carga skill .openclaw/skills/wally-commands/morning/SKILL.md
3. Skill instruye al LLM:
   - mcp__wally__detect_regime(profile=active)
   - mcp__wally__macro_gate_check()
   - mcp__wally__sentiment_score()
   - mcp__tradingview__quote_get(...)
   - dentro de wally MCP: lee positions abiertas via memory.read_signals(status="pending")
4. wally-trader-mcp ejecuta lógica desde shared/wally_core/
5. memory.get_backend(profile).read_signals() → si hybrid: local cache (fast); si stale, sync Notion
6. Resultado JSON → LLM sintetiza → reporte markdown al usuario
```

CC ejecuta exactamente la misma cadena. Cero divergencia funcional.

### Write path

Usuario en OC: `/signal BTCUSDT LONG entry=68000 sl=67500 tp=69000 leverage=10x`

```
1. Skill llama mcp__wally__signal_validate(...)
2. wally-trader-mcp valida (4 filters + ML + multifactor + macro)
3. Si decisión = GO o WARN:
   backend = memory.get_backend("bitunix")  # → HybridBackend
   uuid = backend.append_signal("bitunix", Signal(...))
   # Hybrid:
   #   1. write a local CSV/MD con uuid (sync, locked) — DONE
   #   2. enqueue a .notion_pending.jsonl (also locked)
   #   3. background thread drains queue cada 30s → Notion API
4. wally-trader-mcp devuelve uuid + decisión al LLM
5. LLM presenta reporte al usuario
6. Mientras tanto: CC en otra terminal corre /status → backend.read_signals(profile="bitunix")
   → ve la nueva fila local INMEDIATAMENTE (mismo filesystem)
   → o desde Notion si está corriendo en otra Mac (próximo sync interval)
```

### Conflictos cross-harness

**Misma máquina, dos terminales (CC + OC, ambos backend=hybrid):**
- Ambos leen del mismo `.claude/profiles/<name>/memory/` → consistente
- Ambos escriben con flock → serializado
- Ambos enqueue a la misma `.notion_pending.jsonl` → flock idem
- Background sync drena queue compartida → Notion siempre converge

**Distinta máquina (Mac casa + Mac oficina, ambas backend=hybrid):**
- Cada Mac tiene su `.claude/profiles/<name>/memory/` local distinto
- Notion es la fuente de verdad para cross-device
- Reads disparan refresh de local cache desde Notion (si stale >5min)
- Writes en Mac A se ven en Mac B después del próximo sync (≤30s)
- **Si trabajaste en Mac A y vas a Mac B:** corré `make sync-pull PROFILE=<name>` antes de empezar — fuerza refresh full desde Notion

**Mismo usuario vs hermano:** API keys distintas → workspaces distintos → cero overlap. Imposible que un escenario lea data del otro.

### Health & telemetry

`wally_core/health.py` chequea al inicio de critical paths:
- `mcp__wally__ping()` con timeout 2s
- `mcp__tradingview__tv_health_check()`
- `memory.get_backend(profile).health_check()` — backend-specific:
  - LocalBackend: filelock libre, archivos legibles
  - NotionBackend: API responde, DBs existen, rate limit OK
  - HybridBackend: ambos + queue drain status (depth, last sync)
- Profile válido (`WALLY_PROFILE`)
- Macro cache fresh (<24h)

CC ya tiene esto parcial; OC lo invoca desde skill `/doctor`.

## Error Handling

### Modos de falla y respuestas

| Falla | Detección | Respuesta | Recuperación |
|---|---|---|---|
| `wally-trader-mcp` no responde | Health check o timeout 5s | Skills caen a fallback bash (`python3 -m wally_core.<module> --json`) | Auto-retry next call |
| TradingView MCP cae | `tv_health_check()` falla | NO operar nuevos trades. Read-only workflows siguen | Manual: `tv_launch` |
| Notion MCP cae (backend=hybrid) | `health_check()` falla | Writes locales OK; queue de pending Notion writes crece. Reads de local cache | Auto-drain cuando Notion vuelva |
| Notion MCP cae (backend=notion only) | Idem | Writes BLOQUEADOS (error claro). Reads degradan a último cache si existe | Manual: switch a hybrid o esperar |
| Notion rate limit (HTTP 429) | Response code | Exponential backoff (1s/2s/4s, 3 retries). Si persiste → enqueue local | Auto |
| Anthropic API down (CC) | SDK error | OC sigue funcionando. Si OC también Anthropic → fallback OpenRouter si opt-in | Sin acción |
| Filelock timeout 5s | Otro proceso writing >5s | Error: "concurrent write detected". Reintento manual | Manual |
| Stale lock (.lock con PID muerto) | Auto-detected (age >60s + PID gone) | Auto-cleanup antes de reintentar | Auto |
| Profile inválido | Validation entry | Error: "profile foo not found". Aborta | Manual |
| Macro cache stale (>24h) | Health check | Auto-refresh online; warning offline | Auto/manual |
| MT5 bridge down (ftmo/fundingpips) | Guardian falla | NO permitir trades en esos profiles | Manual |
| Schema drift en Notion DB (column missing) | Schema check al write | Aborta + log a `notion_schema_errors.log`. **No corrupts DB.** | Manual: `make notion-migrate` re-aligns schema |
| Schema drift en `signals_received.csv` (local) | Schema check al write | Aborta + log a `bitunix_log_errors.log` | Manual |
| Conflict cross-device (Mac A y B writing simultaneous) | Detected al sync (UUIDs duplicados raros, timestamps cruzados) | Last-write-wins por timestamp. Both UUIDs preserved. Conflict logged | Manual: revisar log si raro |
| `wally_core` import fail | ImportError al lanzar MCP | MCP no arranca → fallback bash o "MCP unavailable" | `make doctor` |

### Principios

1. **Boundaries explícitos.** Validación solo en tool entry points y al leer archivos del usuario. Lógica interna confía en sus inputs.
2. **Fallar ruidoso.** Errores con stack trace al usuario. Nunca silenciar.
3. **Estado nunca inconsistente.** Writes append-only o atómicos (temp+rename). Schema drift → abort antes de escribir.
4. **Health check antes de critical paths.** `signal_validate`, `journal_close`, `hunt_signals` corren `health_check()` first.
5. **Fallback bash es contrato.** wally-trader-mcp es opcional para correctness; obligatorio solo para latencia/UX.
6. **Hybrid es safe-by-default.** Local primary garantiza UX instant; Notion mirror garantiza cross-device. Ninguna falla de Notion bloquea sesión.

### Recovery scenarios

- **A: usuario cierra OC mid-write.** Proceso muere → flock libera. Si lock huérfano: próximo write detecta PID muerto y limpia. Buffer flush antes de release.
- **B: CC y OC corren `/journal` simultáneo.** flock serializa. Ambos persisten. Notion async sync converge eventualmente.
- **C: wally-trader-mcp se reinicia.** Stateless — restart siempre seguro. Skills caen a fallback bash mientras tanto.
- **D: Notion API rate limit.** Backoff exponencial. Si persiste, queue local crece. Drain en próximo health OK.
- **E: Brother instala el sistema.** `make notion-init` con su API key. `make notion-migrate` con su data inicial (vacía o importada). Su workspace queda independiente.
- **F: Cross-device session.** User cierra Mac A en CR 12:00, abre Mac B en CR 14:00. Mac B corre `make sync-pull PROFILE=bitunix` → refresh local desde Notion → sigue donde Mac A dejó.

### Logging

```
logs/<YYYY-MM-DD>/
├── wally-mcp.log          # MCP server stdout/stderr
├── cc-skills.log, oc-skills.log
├── locking.log            # filelock contention
├── notion-sync.log        # hybrid drain events, rate limits, conflicts
├── notion_schema_errors.log
└── bitunix_log_errors.log
```

Rotación: `logrotate` 30 días. No se commitea.

## Testing

### Pirámide

```
                  ┌──────────────────┐
                  │ E2E paridad CC↔OC│  ~5 tests, manual+nightly
                  │ + cross-device   │
                  └──────────────────┘
                ┌──────────────────────┐
                │ Integration MCP+state│  ~30 tests, CI cada PR
                │ + Notion sandbox     │
                └──────────────────────┘
              ┌──────────────────────────┐
              │ Unit wally_core/* + locks│  ~150 tests, CI cada commit
              │ + 3 memory backends      │
              └──────────────────────────┘
```

### Unit (`shared/wally_core/tests/`)

| Módulo | Cobertura | Casos críticos |
|---|---|---|
| `regime.py` | 90% | RANGE/TRENDING/VOLATILE labels + ADX edges |
| `validate.py` | 95% | 4-filter LONG/SHORT, NO-GO if any filter fails |
| `risk.py` | 95% | flat 2%, VaR, parity, leverage caps |
| `hunt.py` | 85% | scoring 0-100, top-pick, tier-0 filter |
| `journal.py` | 90% | Sharpe, Max DD, IC sobre fixtures |
| `signals.py` | 95% | append + schema validation + outcome closure |
| `locking.py` | 100% | timeout, stale cleanup, retry |
| `macro.py` | 80% | event windows, DST, cache freshness |
| **`memory/local.py`** | 95% | Append + read + schema enforcement + concurrent writes |
| **`memory/notion.py`** | 90% | CRUD operations + rate limit handling + schema drift |
| **`memory/hybrid.py`** | 90% | Queue drain + conflict resolution + offline fallback |
| **`memory/migrate.py`** | 85% | CSV→Notion idempotent + dry-run + rollback |

Framework: pytest. Notion tests usan **VCR.py** para cassette responses (no real API in unit). Fixtures en JSON para OHLCV.
Comando: `make test-unit` → < 60s.

### Integration (`wally-trader-mcp/tests/`)

| Test | Qué valida |
|---|---|
| `test_mcp_handshake.py` | Server responde a `initialize` |
| `test_tool_<name>.py` (×12) | Cada tool: input → JSON shape esperada |
| `test_concurrent_writes.py` | 5 procesos paralelos a CSV → 5 filas, sin corrupción |
| `test_fallback_bash.py` | Apaga MCP → script bash da output equivalente |
| `test_profile_isolation.py` | profile=bitunix no lee/escribe memory de profile=ftmo |
| `test_health_check.py` | health detecta TV/MCP/Notion down, profile inválido, cache stale |
| **`test_notion_sandbox.py`** | Real Notion sandbox workspace: CRUD, schema check, rate limit handling |
| **`test_hybrid_offline.py`** | Notion API mocked-down → writes encolan, drain on recovery |

Framework: pytest + mcp Python SDK. Subprocess para arrancar/matar server.
Comando: `make test-integration` → ~3min.

### Adapter transform (`adapters/openclaw/test_transform.py`)

Mismo molde que `adapters/hermes/test_transform.py`. Cubre:
- agent → skill frontmatter (mapping toolsets)
- command → skill (basic, argument-hint, slash naming)
- clean_group (orphan removal)
- MCP entry projection a `.openclaw/config.json`
- OpenRouter opt-in genera config diferente
- **Notion MCP entry incluido en config** con env var passthrough

### Paridad CC ↔ OC + cross-device

Suite `tests/parity/`:

| Test | Workflow | Comparación |
|---|---|---|
| `parity_morning.sh` | `/morning` profile bitunix sobre snapshot | Reporte structure-equivalent |
| `parity_punk_hunt.sh` | `/punk-hunt` mercado congelado | Top pick + score ±0 |
| `parity_validate.sh` | `/validate` setup específico | GO/NO-GO + razón exact match |
| `parity_risk.sh` | `/risk` 5 escenarios | Position size ±$0.01 |
| `parity_journal.sh` | `/journal` con trade log fixture | Sharpe/WR/PF ±0.001 |
| `parity_signal.sh` | `/signal BTCUSDT LONG ...` | Score + GO/NO-GO exact |
| **`parity_memory_hybrid.sh`** | CC escribe signal → OC lee → mismo UUID, mismo data | Estructura idéntica desde ambos backends |
| **`parity_cross_device.sh`** | Simula 2 instalaciones (different PROFILE_HOME), Notion compartido vía sandbox key | Convergencia eventual de DBs |

Comando: `make test-parity` → ~15 min. Nightly cron.

### E2E (manual + scripted)

7 escenarios completos:

1. **Morning session bitunix:** CC → `/punk-morning` → output esperado. OC repite → equivalente.
2. **Live signal validate:** signal Discord → `/signal BTC LONG ...` → auto-log → verificar fila desde otro harness via Notion.
3. **End-of-day journal:** `/journal` con día sintético → métricas + equity_curve actualizada en Notion DB.
4. **Concurrent writes:** CC y OC `/signal` simultáneo → CSV + Notion ambos consistentes, no corrupción.
5. **Fallback path:** matar wally-trader-mcp → skills caen a bash transparente.
6. **Notion offline simulation:** `iptables` block Notion API → writes encolan, drain on recovery.
7. **Cross-device handoff:** simulate Mac casa → Mac oficina via copy de `.claude/profiles/` con cleared local memory + sync-pull.

Documentados en `tests/e2e/scenarios.md`. Manual cada release menor.

### CI matrix

| Trigger | Tests | Duración |
|---|---|---|
| Cada commit feature branch | unit | <60s |
| Cada PR | unit + integration (sin sandbox Notion) + lint + adapter transform | ~4min |
| Merge a main | unit + integration full + paridad | ~18min |
| Nightly cron | todo + e2e scripted (1-5) + sandbox Notion | ~40min |
| Pre-release | e2e completo + manual scenarios 6, 7 | ~1.5h |

**Notion sandbox workspace:** una cuenta dedicada (`wally-trader-test@...`) con DBs ephemeral. Tests crean/destruyen pages, nunca tocan workspaces de prod.

### Validación operativa post-deploy

- [ ] 7 días corriendo CC + OC en paralelo, mismo profile bitunix, sin discrepancias en signals (local + Notion)
- [ ] Al menos 1 trade real ejecutado vía workflow OC con backend hybrid
- [ ] Cross-device handoff probado al menos 1 vez (simulado o con segunda Mac)
- [ ] Hermano instala el sistema following `docs/openclaw-setup.md` step-by-step → su workspace funciona aislado
- [ ] `make doctor` verde en ambas instalaciones
- [ ] Documentación validada por terceros

## OpenRouter (opt-in)

OpenRouter es **provider de modelos dentro de OpenClaw**, no integración separada con Claude Code.

Casos de uso:
- A/B test de modelos (Kimi, GPT-5, Gemini, Llama) para tareas específicas
- Acceso a modelos no-Anthropic sin manejar múltiples API keys

Activación:
```bash
WALLY_USE_OPENROUTER=1 bash adapters/openclaw/install.sh
```

`.openclaw/config.json` se genera con:
```json5
{
  env: { OPENROUTER_API_KEY: "$OPENROUTER_API_KEY" },
  agents: { defaults: { model: { primary: "openrouter/auto" } } }
}
```

Limitaciones:
- Pierde prompt caching nativo de Anthropic en proxy OpenAI-compat
- `serviceTier` y features Anthropic-specific no se reenvían

Default (sin opt-in): Anthropic API directa, mejor performance.

## Riesgos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Schema OpenClaw cambia mid-desarrollo | Media | Alto | Pin versión en install.sh; revisar release notes mensual |
| Notion API rate limits bloquean writes | Media | Medio | Hybrid backend encolas localmente; backoff exponencial; rate limit configurable per-profile |
| Notion DBs se borran/corrompen accidentalmente | Baja | **Crítico** | Local cache funciona como backup. `make notion-rollback` exporta a CSV. Notion's own version history (90d retention free tier) |
| Filelock contention bajo concurrencia | Baja | Bajo | Timeout 5s + retry; logging |
| `wally-trader-mcp` introduce bugs vs scripts originales | Media | Alto | Golden-file tests por tool; fallback bash siempre |
| `wally_core` refactor rompe scripts | Media | Medio | CI tests sobre scripts pre y post; rollout gradual módulo por módulo |
| OpenRouter caching loss reduce calidad | Baja | Bajo | Opt-in only; default Anthropic directo |
| MCP servers no arrancan en clean install | Media | Alto | `make doctor` cubre; install.sh valida deps |
| Notion API key del hermano leakea (env mal seteado) | Baja | Alto | Documentar `.env` per-user, `.gitignore` estricto, no commitear keys jamás |
| Cross-device sync conflict (poco frecuente) | Baja | Medio | Last-write-wins por timestamp; conflicts logged; manual resolve si raro |
| `@notionhq/notion-mcp-server` no fit | Media | Medio | Fase 1 valida; alternativas: `@suekou/mcp-notion-server` o cliente custom thin |

## Implementación: orden de fases

Las fases son secuenciales — cada una bloquea a la siguiente.

1. **Fase 1 (semana 1):** `shared/wally_core/` esqueleto + módulos puros (regime, validate, risk, locking, journal, signals). Tests unit. Cero cambio en scripts existentes. **Validar Notion MCP server choice + sandbox workspace.**
2. **Fase 2 (semana 1-2):** `shared/wally_core/memory/` (interface + LocalBackend + schemas). Tests unit. Scripts existentes refactor para usar `LocalBackend` (cero cambio funcional).
3. **Fase 3 (semana 2):** `shared/wally_core/memory/notion.py` + `migrate.py`. Notion sandbox tests. `make notion-init`, `make notion-migrate`.
4. **Fase 4 (semana 2-3):** `HybridBackend` + queue drain + offline fallback + cross-device tests. Switch default backend a `hybrid`.
5. **Fase 5 (semana 3):** `wally-trader-mcp/` con primeras 6 tools (read-only) usando memory abstraction. Tests integration.
6. **Fase 6 (semana 3-4):** `wally-trader-mcp/` completo (12 tools). Refactor scripts críticos para usar wally_core. Paridad CC contra scripts pre-refactor.
7. **Fase 7 (semana 4):** `adapters/openclaw/` (mold de hermes) + `.openclaw/` config. Install.sh, transform.py, tests. OpenRouter opt-in.
8. **Fase 8 (semana 4-5):** Tests paridad CC↔OC + cross-device. E2E scripted. `make doctor`.
9. **Fase 9 (semana 5):** Validación operativa 7 días. docs/openclaw-setup.md + docs/notion-memory-setup.md. Setup guide para hermano.
10. **Release:** merge a main.

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

### B. Notion DBs schema (canonical, auto-creado por migrate.py)

```
📊 Profiles (DB)
  - Title (title): nombre profile (bitunix, retail, ftmo...)
  - Capital USD (number)
  - Capital BTC (number, opcional)
  - Strategy (select): Mean Reversion | Donchian Breakout | MA Crossover | Multi-Asset
  - Window CR (text): "06:00-23:59"
  - Last Updated (last_edited_time)

📈 Trades Log (DB)
  - Title (title): UUID auto
  - Profile (relation → Profiles)
  - Date (date)
  - Asset (text): "BTCUSDT.P", "EURUSD", etc.
  - Side (select): LONG | SHORT
  - Entry (number)
  - SL (number)
  - TP1, TP2, TP3 (number)
  - Leverage (number)
  - Position Size USD (number)
  - Exit Price (number, nullable)
  - PnL USD (number)
  - PnL % (number)
  - R Multiple (number)
  - Status (select): open | tp1_hit | tp2_hit | tp3_hit | sl | closed_manual
  - Source (select): manual | signal | hunt | copy
  - Notes (rich text)

📡 Signals Received (DB)
  - Title (title): UUID auto
  - Timestamp (created_time)
  - Profile (relation → Profiles)
  - Source (select): discord | punk-hunt | self
  - Symbol (text)
  - Side (select): LONG | SHORT
  - Entry, SL, TP1, TP2, TP3, Leverage (numbers)
  - Score (number, 0-100)
  - Decision (select): GO | NO-GO | WARN
  - Outcome (select): TP1 | TP2 | TP3 | SL | manual | pending
  - Exit Price (number, nullable)
  - PnL USD (number, nullable)
  - Raw Message (rich text): el mensaje original Discord/CLI

💰 Equity Curve (DB)
  - Title (title): "<profile>-<date>"
  - Profile (relation → Profiles)
  - Date (date)
  - Equity USD (number)
  - Equity BTC (number, opcional)
  - Daily PnL USD (number)
  - Daily Return % (number)

📔 Daily Journal (DB-pages)
  - Title (title): "<profile>-<date>"
  - Profile (relation → Profiles)
  - Date (date)
  - Summary (rich text)
  - Lessons (rich text)
  - Screenshots (files)

📅 Weekly Digest (DB-pages)
  - Title (title): "<year>-Wnn"
  - Week Start (date)
  - Summary (rich text)
  - Highlights (rich text)
  - Macro Events Next Week (rich text)
```

### C. Comandos de uso final

Setup primera vez (post-merge):
```bash
make wally-mcp-install
make notion-init                          # interactive: API key, workspace
make notion-migrate PROFILE=bitunix        # migra histórico a Notion
make notion-migrate PROFILE=retail
# ... repetir para los 7 profiles
bash adapters/openclaw/install.sh
make doctor
```

Hermano (instalación independiente):
```bash
git clone <repo>
cd wally-trader
make wally-mcp-install
export NOTION_API_KEY="<su_key>"
make notion-init                          # crea su workspace
# (opcional) make notion-migrate si tiene histórico CSV
bash adapters/openclaw/install.sh
make doctor
```

Día a día (sin cambios para CC):
```bash
$EDITOR system/commands/morning.md        # CC ve cambio inmediato
git commit -am "fix morning"              # pre-commit regenera adapters
```

OpenClaw uso:
```bash
openclaw agent --message "/morning"
openclaw mcp list                         # ver MCP servers (tradingview, wally, notion)
openclaw skills list
```

Cross-device handoff:
```bash
# En Mac B antes de empezar:
make sync-pull PROFILE=bitunix            # forzar refresh local desde Notion
```

### D. Referencias

- Spec previa: `docs/superpowers/specs/2026-04-22-multi-cli-portability-design.md`
- OpenClaw docs: https://docs.openclaw.ai
- OpenClaw skills format: https://docs.openclaw.ai/tools/creating-skills.md
- OpenClaw MCP: https://docs.openclaw.ai/cli/mcp.md
- OpenClaw OpenRouter: https://docs.openclaw.ai/providers/openrouter.md
- Notion API: https://developers.notion.com
- Notion MCP servers: `@notionhq/notion-mcp-server`, `@suekou/mcp-notion-server`
- agentskills.io standard (formato shared con Hermes)
