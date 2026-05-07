# OpenClaw adapter (v1 — soporte total)

Genera `.openclaw/skills/` desde `system/` para que [OpenClaw](https://openclaw.ai) cargue el sistema Wally Trader como skills nativos.

<!-- TODO: refine narrative for OpenClaw once upstream docs are stable. Current adapter is based on agentskills.io compatibility (same standard as Hermes/OpenCode). -->

## Conceptual mapping

OpenClaw NO tiene "subagents" ni "slash commands" como filesystem entries. Todo se proyecta como **skills** (estándar [agentskills.io](https://agentskills.io)):

| Source CC entity | OpenClaw destination | Slash invocation |
|---|---|---|
| `system/agents/<name>.md` | `.openclaw/skills/wally-agents/<name>/SKILL.md` | activated by description match |
| `system/commands/<name>.md` | `.openclaw/skills/wally-commands/<name>/SKILL.md` | `/<name>` (skill name = trigger) |
| `system/skills/<name>/` | `.openclaw/skills/wally-skills/<name>/` (symlink) | activated by description match |
| `AGENTS.md` (root) | (no copy needed — OpenClaw reads it natively) | — |
| `CLAUDE.md` (root) | (no copy needed — OpenClaw reads it as fallback context) | — |

## Primera vez

```bash
bash adapters/openclaw/install.sh
```

Hace:
1. Genera `.openclaw/skills/wally-agents/` (12 skills desde agents)
2. Genera `.openclaw/skills/wally-commands/` (29 skills desde commands)
3. Symlinks `.openclaw/skills/wally-skills/ → ../../system/skills` (passthrough, 14 skills sin transformar)
4. Si OpenClaw está instalado (`~/.openclaw/` existe): symlinks `~/.openclaw/skills/wally-trader/ → <repo>/.openclaw/skills/`
5. Instala git pre-commit hook v1 (auto-sync futuro)

## Auto-sync via git hook

Cada commit que toca `system/commands/` o `system/agents/` regenera `.openclaw/skills/` y lo agrega al mismo commit. Sin overhead manual.

## MCP TradingView (opcional)

El schema exacto de MCP en `~/.openclaw/config.yaml` no está completamente documentado en upstream. OpenClaw soporta MCP pero la configuración se hace vía CLI:

```bash
openclaw config set mcp.tradingview.command node
openclaw config set mcp.tradingview.args '["./tradingview-mcp/src/server.js"]'
openclaw config set mcp.tradingview.cwd /Users/josecampos/Documents/wally-trader
```

O via el wizard `openclaw setup` que pregunta por servers MCP interactivamente.

## Translations aplicadas

### Agents → Skills (`wally-agents/`)
- `name`, `description` → preservados
- `tools: A, B, C` (CC) → `metadata.openclaw.requires_toolsets: [terminal, mcp, web, subagents]` (OpenClaw) según mapeo:
  - `mcp__*` → `mcp`
  - `WebFetch`, `WebSearch` → `web`
  - `Agent` → `subagents`
  - default siempre incluye `terminal`
- Body preservado con header de provenance (HTML comments)

### Commands → Skills (`wally-commands/`)
- `description` → preservado
- `argument-hint: <args>` → embebido como `<!-- args: <args> -->` en el body
- `allowed-tools` → descartado (OpenClaw resuelve tools dinámico)
- Filename → skill name → slash trigger (`morning.md` → `/morning`)
- Body preservado con header de provenance + nota de invocación

### Skills (`wally-skills/`)
- Symlink directo a `system/skills/` — formato agentskills.io ya compatible
- Zero translation
- Soporta refresh inmediato cuando edita `system/skills/`

## Tests

```bash
python3 -m pytest adapters/openclaw/test_transform.py -v
```

12 tests cubren:
- agent → skill frontmatter (basic, MCP toolset, web toolset, subagents toolset, no-tools default)
- agent body preservation con provenance header
- command → skill (basic, argument-hint, slash naming, no-frontmatter)
- clean_group (orphan removal, missing-dir no-op)

## Troubleshooting

- `.openclaw/skills/` stale después de edit: `bash adapters/openclaw/install.sh` regenera
- Git hook no triggerea: verifica `ls .git/hooks/pre-commit` existe y tiene marker `openclaw-adapter-v1`
- PyYAML not found: `pip3 install pyyaml`
- OpenClaw no encuentra skills: verifica que `~/.openclaw/skills/wally-trader/` es symlink válido a `<repo>/.openclaw/skills/`
- Skill no aparece en `/skills`: verifica que `SKILL.md` tiene frontmatter válido (yaml syntax)

## Diferencias OpenClaw vs OpenCode vs Claude Code

<!-- TODO: refine OpenClaw-specific capabilities once upstream docs are complete. -->

| Feature | Claude Code | OpenCode | OpenClaw |
|---|---|---|---|
| Subagents | ✅ `.claude/agents/` | ✅ `.opencode/agents/` | ❌ — proyecta a skills |
| Slash commands | ✅ `.claude/commands/` | ✅ `.opencode/commands/` | ⚠️ proyectado a skills (works) |
| Skills | ✅ `~/.claude/skills/` | ✅ `~/.config/opencode/skills/` | ✅ `~/.openclaw/skills/` (primary) |
| Cron scheduling | ❌ | ❌ | TODO: confirm OpenClaw cron support |
| Multi-platform delivery | ❌ | ❌ | TODO: confirm OpenClaw channels |
| Serverless backend | ❌ | ❌ | TODO: confirm OpenClaw backends |
| Voice memo | ❌ | ❌ | TODO: confirm OpenClaw voice support |
| Context file | `CLAUDE.md` | `AGENTS.md` + `CLAUDE.md` | `OPENCLAW.md` > `AGENTS.md` > `CLAUDE.md` |
| MCP | ✅ user-scope | ✅ project + user | ✅ via `openclaw config set` |
