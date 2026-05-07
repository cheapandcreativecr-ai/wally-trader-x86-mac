# OpenClaw Setup Guide

Get the Wally Trader system running under OpenClaw in under 10 minutes.

---

## 1. Prerequisites

| Tool | Version | Check |
|---|---|---|
| **Node.js** | 22+ (for OpenClaw runtime) | `node --version` |
| **Python** | 3.11+ | `python3 --version` |
| **uv** | latest | `uv --version` |
| **npx** | included with Node | `npx --version` |
| **OpenClaw** | latest | `openclaw --version` |

Install `uv` if missing:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Install OpenClaw (see https://openclaw.ai for the latest install command):
```bash
npm install -g @openclaw/cli
```

---

## 2. One-time install

```bash
# 1. Clone the repo
git clone https://github.com/your-org/wally-trader.git
cd wally-trader

# 2. Create the Python venv + install wally_core and wally-trader-mcp
uv venv shared/wally_core/.venv --python 3.11
make wally-mcp-install

# 3. Generate .openclaw/skills/ from system/
bash adapters/openclaw/install.sh

# 4. Verify everything
make doctor
```

Expected `make doctor` output (green path):
```
=== wally-trader doctor ===
[1/8] Python deps...
  wally_core 0.1.0
  wally_trader_mcp ok
[2/8] Profile env...
  WALLY_PROFILE=unset
  WALLY_MEMORY_BACKEND=hybrid (default)
[3/8] Memory backend...
   {"backend": "hybrid", "status": "ok", ...}
[4/8] Macro cache...
  cache age: 2h
[5/8] TradingView MCP...
  tradingview-mcp/src/server.js exists
[6/8] OpenClaw skills...
  agents=17 commands=44
[7/8] Notion (if hybrid)...
  NOTION_API_KEY set
[8/8] Locks...
  no stale locks
=== done ===
```

Warnings for missing `NOTION_API_KEY` and stale macro cache are expected on first run — see sections 4 and 6 below.

---

## 3. Daily use

All Wally Trader slash commands are mirrored as OpenClaw skills.

**Morning session:**
```bash
openclaw agent --message "/punk-morning"
```

**Regime check:**
```bash
openclaw agent --message "/regime"
```

**Scan for setups every hour:**
```bash
openclaw agent --message "/punk-hunt"
```

**Validate a Discord signal:**
```bash
openclaw agent --message "/signal ETHUSDT SHORT entry=2400 sl=2450 tp=2300 leverage=10"
```

**Close a trade outcome:**
```bash
openclaw agent --message "/log-outcome ETHUSDT TP1 2300 --pnl 2.50"
```

**Profile switch:**
```bash
WALLY_PROFILE=bitunix openclaw agent --message "/status"
```

Skills live in `.openclaw/skills/wally-commands/` (slash commands) and `.openclaw/skills/wally-agents/` (background agents). Run `openclaw skills list` to see all loaded skills.

---

## 4. OpenRouter opt-in

To route LLM calls through [OpenRouter](https://openrouter.ai) instead of the default provider:

```bash
export OPENROUTER_API_KEY=sk-or-...
WALLY_USE_OPENROUTER=1 bash adapters/openclaw/install.sh
```

This regenerates `.openclaw/skills/` with OpenRouter model refs embedded in each skill's frontmatter.

To revert: `bash adapters/openclaw/install.sh` (without `WALLY_USE_OPENROUTER`).

---

## 5. Cross-harness use (CC + OC simultaneously)

Claude Code and OpenClaw can run side-by-side. Both read from the same memory layer:

```
.claude/profiles/<profile>/memory/   ← shared on-disk state
```

**Key rule:** `WALLY_PROFILE` is per-terminal. Set it explicitly in each terminal window to avoid cross-profile contamination.

```bash
# Terminal A — Claude Code, bitunix
export WALLY_PROFILE=bitunix
claude

# Terminal B — OpenClaw, ftmo
export WALLY_PROFILE=ftmo
openclaw agent --message "/status"
```

Memory writes from one harness are immediately visible to the other because both use the same CSV/JSON files via `wally_core.memory.LocalBackend` (or Notion hybrid if `NOTION_API_KEY` is set).

Avoid running the same profile in both terminals simultaneously — concurrent writes are safe (file locking in `wally_core.locking`) but confusing in practice.

---

## 6. Troubleshooting

### NOTION_API_KEY missing
Expected if you have not set up Notion. Memory falls back to local CSV. See `docs/notion-memory-setup.md` if you want cross-device sync.

### TradingView MCP not built
```bash
cd tradingview-mcp && npm install && npm run build
```

### Skills not appearing in OpenClaw
```bash
# Regenerate
bash adapters/openclaw/install.sh

# Check symlink
ls -la ~/.openclaw/skills/wally-trader

# Should point to:
# <repo>/.openclaw/skills -> ~/.openclaw/skills/wally-trader
```

### wally_trader_mcp NOT installed
```bash
make wally-mcp-install
```

### MCP server errors on startup
Verify the wally MCP server entry in `system/mcp/servers.json` matches the actual installed path. Run `make doctor` — the memory backend check (step 3) will surface errors.

### Stale macro cache warning
Refresh manually:
```bash
shared/wally_core/.venv/bin/python .claude/scripts/macro_calendar.py
```

Or activate the launchd timer for automatic daily refresh:
```bash
cp .claude/launchd/com.wally.macro-calendar.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.wally.macro-calendar.plist
```

### PyYAML not found during install.sh
```bash
pip3 install pyyaml
# or: uv pip install pyyaml --python shared/wally_core/.venv/bin/python
```
