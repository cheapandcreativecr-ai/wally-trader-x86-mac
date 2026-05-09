# Hermes Operational Layer — Setup Guide

> **Two supported hosts:** macOS (everything on one machine) or Windows 11 + WSL Ubuntu (Hermes/wally MCP in Linux, TV MCP bridged into Windows native). Most steps are shared; jump to the [WSL section](#setup-on-windows-11--wsl-ubuntu) for the cross-OS bridge details.

## What this enables

Send `/punk-hunt` from your phone's Telegram → Hermes (running on your Mac or WSL host) receives it → invokes MCP tools → draws levels on TradingView Desktop — all from anywhere in the world.

```
You (Telegram mobile)
        │  /punk-hunt
        ▼
┌──────────────────────┐
│  Telegram Bot API    │
└──────────┬───────────┘
           │  webhook / polling
           ▼
┌──────────────────────────────────────────────────────┐
│  Hermes daemon  (your Mac, always-on)                │
│  ~/.hermes/skills/wally-trader/  ← symlinked         │
│    wally-commands/  wally-agents/  wally-skills/     │
└────────┬─────────────────────────┬───────────────────┘
         │                         │
         ▼                         ▼
┌────────────────┐       ┌──────────────────────┐
│  wally MCP     │       │  tradingview MCP      │
│  (Python venv) │       │  (Node.js, TV Desktop)│
│  12 tools      │       │  78 tools             │
└────────────────┘       └──────────┬────────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  TradingView Desktop  │
                         │  chart redraws live   │
                         └──────────────────────┘
```

---

## Prerequisites

- Mac with TradingView Desktop installed and logged in to your account
- Telegram account + ability to create a bot via @BotFather
- Python 3.11+ (`python3 --version`)
- Node.js 18+ (`node --version`) — for tradingview-mcp
- `uv` package manager (`pip install uv` or `brew install uv`)
- Repo cloned at `/Users/josecampos/Documents/wally-trader`

---

## Step 1 — Install Hermes

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

Verify:
```bash
hermes --version
```

If `hermes` is not found after install, add it to your PATH:
```bash
export PATH="$HOME/.hermes/bin:$PATH"   # add to ~/.zshrc
```

Configure model and provider (first-time setup):
```bash
hermes setup
```

---

## Step 2 — One-time project setup

Install Python MCP deps (wally + wally-trader-mcp into venv):
```bash
make wally-mcp-install
```

Install/refresh the Hermes adapter (generates skills, symlinks, registers MCPs):
```bash
make hermes-install
```

This single command does three things:
1. Generates `.hermes/skills/wally-{agents,commands,skills}/` from `system/`
2. Symlinks `~/.hermes/skills/wally-trader/` → `.hermes/skills/`
3. Registers all three MCP servers (`tradingview`, `wally`, `notion`) in Hermes config

Verify everything is wired up:
```bash
make hermes-smoke
```

Expected output: `6/6 checks passing`.

---

## Step 3 — Telegram bot setup

### Interactive setup (recommended)

```bash
make hermes-telegram-setup
```

Walks you through token → @getMe validation → chat_id auto-discovery (polls
Telegram for your first inbound message) → allowlist → confirmation message.
Idempotent — safe to re-run after rotating the token.

### Manual setup (if interactive fails)

1. Open Telegram → search for **@BotFather** → `/newbot`
2. Follow prompts → copy the **bot token** (looks like `7123456789:AAF...`)
3. Register it with Hermes:

```bash
hermes config set telegram.bot_token 7123456789:AAFyourTokenHere
```

4. Send any message to your new bot in Telegram
5. Fetch updates:

```bash
curl -s "https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates" | python3 -m json.tool | grep '"id"'
```

6. The number next to `"id"` under `"chat"` is your chat_id (e.g. `123456789`)
7. Allowlist it:

```bash
hermes config set telegram.allowed_chat_ids '[123456789]'
```

### Test connection (before daemon)

```bash
hermes serve   # or: hermes bot  — adjust if your version differs
```

Send `/status` from Telegram → you should get a response within a few seconds.
Press Ctrl+C to stop (we'll daemonize it in the next step).

---

## Step 4 — Daemon setup (Mac always-on)

Load the launchd plist so Hermes starts automatically on login and restarts on crash:

```bash
make hermes-daemon-install
```

> **Important — confirm daemon command first.**  
> The plist defaults to `hermes serve`. If your Hermes version uses a different
> subcommand, edit `.claude/launchd/com.wally.hermes-daemon.plist` first:
>
> ```bash
> # Check what subcommand your Hermes uses:
> hermes --help | grep -E 'serve|bot|daemon|run'
> ```
>
> Then update the `<string>serve</string>` line accordingly.

**Prevent Mac sleep** (so the daemon keeps running):
- System Settings → Energy → Power Adapter → enable "Prevent automatic sleeping when display is off"

Verify daemon is running:
```bash
launchctl list | grep hermes
# Should show: com.wally.hermes-daemon   0   (exit code 0 = running OK)
```

Check the log:
```bash
tail -f logs/hermes-daemon.log
```

---

## Step 5 — Test Telegram → TradingView

With the daemon running and TradingView Desktop open on your chart:

**Basic test** (no TV needed):
```
Telegram: /status
```
Should respond with your current profile + market snapshot within ~30 seconds.

**TradingView drawing test**:
```
Telegram: /regime
```
Should respond with BTC regime analysis (calls wally MCP internally).

```
Telegram: /chart
```
Should clear TradingView and redraw current setup (calls tradingview MCP).

```
Telegram: /punk-hunt
```
Full autonomous scan → scores all bitunix assets → picks best setup → draws on TV.

---

## Daily operations

| Command | What it does |
|---|---|
| `/punk-morning` | Pre-session scan + Neptune TV setup |
| `/punk-hunt` | Autonomous setup scan, score≥70 |
| `/signal BTCUSDT SHORT entry=104000 sl=105500 tp=101000 leverage=10` | Validate Discord signal |
| `/regime` | Market regime detection (ADX + Donchian) |
| `/status` | Current profile dashboard |
| `/journal` | End-of-day log + equity update |

---

## Makefile reference

```bash
# Setup
make hermes-install            # install/refresh adapter + register MCPs (WSL-aware)
make hermes-smoke              # base smoke test
make hermes-doctor             # smoke + WSL-specific checks (alias)
make hermes-telegram-setup     # interactive Telegram token + chat_id

# Daemon (macOS)
make hermes-daemon-install     # load launchd plist
make hermes-daemon-uninstall   # unload plist

# Daemon (Linux / WSL)
make hermes-systemd-install    # install systemd-user unit + enable --now
make hermes-systemd-uninstall  # disable + remove unit

# Both
make hermes-restart            # restart daemon (auto-detects launchd vs systemd)
make hermes-logs               # tail logs/hermes-daemon.log
make hermes-status             # daemon status + registered MCPs
```

---

## Troubleshooting

### Hermes not responding to Telegram messages

```bash
# Is the daemon running?
launchctl list | grep hermes

# Is it crashing?
tail -50 logs/hermes-daemon.log

# Restart it manually:
launchctl unload ~/Library/LaunchAgents/com.wally.hermes-daemon.plist
launchctl load   ~/Library/LaunchAgents/com.wally.hermes-daemon.plist
```

### Wrong daemon subcommand (`exec: "hermes": not found` in log)

The plist uses the absolute path `/usr/local/bin/hermes`. If Hermes is installed
elsewhere (e.g. via Homebrew at `/opt/homebrew/bin/hermes`), update the plist:

```bash
which hermes   # → /opt/homebrew/bin/hermes
# Edit .claude/launchd/com.wally.hermes-daemon.plist:
#   change /usr/local/bin/hermes → /opt/homebrew/bin/hermes
make hermes-daemon-uninstall && make hermes-daemon-install
```

### MCP server timeout (tools not responding)

```bash
# Check what command Hermes will use for the wally MCP:
hermes config get mcp.wally.command
# Should return: /Users/josecampos/Documents/wally-trader/shared/wally_core/.venv/bin/python

# If missing, re-register:
bash adapters/hermes/configure_mcp.sh

# Verify venv is installed:
make hermes-smoke  # check 6
```

### TradingView drawing fails

1. TradingView Desktop must be **open and logged in** on the same Mac
2. The chart must be on the correct symbol (e.g. `BINANCE:BTCUSDT.P` for bitunix)
3. Check tradingview-mcp is running:

```bash
hermes config get mcp.tradingview.command
hermes config get mcp.tradingview.args
```

4. Test tradingview-mcp directly:

```bash
node tradingview-mcp/src/server.js
# Should start and wait — press Ctrl+C
```

### Telegram bot token expired or invalid

BotFather tokens don't expire, but if you revoked and re-issued:
```bash
hermes config set telegram.bot_token <new_token>
launchctl kickstart -k gui/$(id -u)/com.wally.hermes-daemon
```

### Chat_id not allowlisted (bot ignores messages)

```bash
hermes config get telegram.allowed_chat_ids
# Should show your chat_id — if empty:
hermes config set telegram.allowed_chat_ids '[YOUR_CHAT_ID]'
```

---

## Setup on Windows 11 + WSL Ubuntu

This is the path when the always-on host is a Windows 11 PC and you want
Hermes + the wally MCP to live in WSL (Linux native, faster Python/venv) while
the **TradingView MCP runs on Windows** (because TV Desktop is Windows-only
and attaches via Chrome DevTools Protocol).

### Architecture (cross-OS)

```
Telegram mobile
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│  Windows 11 PC (always on)                                  │
│  ┌────────────────────────────┐   ┌───────────────────────┐ │
│  │  WSL Ubuntu                │   │  Windows native       │ │
│  │  ┌──────────────────────┐  │   │  ┌─────────────────┐  │ │
│  │  │  Hermes daemon       │  │   │  │ TradingView     │  │ │
│  │  │  (systemd-user)      │  │   │  │ Desktop         │  │ │
│  │  └─────┬─────────┬──────┘  │   │  └────────▲────────┘  │ │
│  │        │         │         │   │           │ CDP       │ │
│  │        ▼         │         │   │           │           │ │
│  │  ┌──────────┐    │         │   │   ┌───────┴───────┐   │ │
│  │  │ wally    │    │         │   │   │ tradingview-  │   │ │
│  │  │ MCP      │    │         │   │   │ mcp (node.exe)│   │ │
│  │  │ (python) │    │         │   │   └───────▲───────┘   │ │
│  │  └──────────┘    │         │   │           │ stdio     │ │
│  │                  │         │   │           │           │ │
│  │  ┌───────────────▼──────┐  │ ──┼─────► (interop)       │ │
│  │  │ wsl_tv_bridge.sh     │──┼───┼──────────┘            │ │
│  │  │ exec node.exe via    │  │   │                        │ │
│  │  │ /mnt/c/.../node.exe  │  │   │                        │ │
│  │  └──────────────────────┘  │   │                        │ │
│  └────────────────────────────┘   └────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Prerequisites (Windows 11 side)

| Component | Where | Notes |
|---|---|---|
| WSL2 Ubuntu | `wsl --install -d Ubuntu` | Make sure systemd is enabled |
| systemd in WSL | `/etc/wsl.conf` → `[boot]\nsystemd=true` then `wsl --shutdown` | Required for `systemctl --user` |
| Node.js (Windows) | https://nodejs.org → MSI installer | Default path `C:\Program Files\nodejs\node.exe` |
| TradingView Desktop | Windows native, signed in to your account | Must be open when Hermes runs |
| Repo cloned twice | Once in WSL (`~/wally-trader`), once in Windows (`C:\Users\<you>\wally-trader`) | Sync with git or `\\wsl$` UNC path |

### Step W1 — One-time setup in WSL

```bash
cd ~/wally-trader
make wally-mcp-install     # python venv + wally_trader_mcp
make hermes-install        # adapter + skills + MCP registration (auto-detects WSL)
```

`configure_mcp.sh` detects WSL via `/proc/sys/kernel/osrelease` and applies
the `tradingview.platform_overrides.wsl` entry from `system/mcp/servers.json`,
which routes the TV MCP through `wsl_tv_bridge.sh` instead of plain `node`.

### Step W2 — Configure the Windows-side bridge

Inside the Windows-side clone, install `tradingview-mcp` deps:

```powershell
# In Windows PowerShell
cd C:\Users\<you>\wally-trader\tradingview-mcp
npm install
```

Back in WSL, create `~/wally-trader/.env` with the Windows path:

```bash
# ~/wally-trader/.env  (gitignored)
TV_MCP_WIN_REPO=C:\Users\jose\wally-trader
WIN_NODE_EXE=/mnt/c/Program Files/nodejs/node.exe
NOTION_API_KEY=secret_xxx        # optional
```

Verify the bridge resolves:

```bash
make hermes-doctor   # smoke test, includes WSL-specific checks
```

You should see:
```
[PASS] WSL: tv bridge script present + executable
[PASS] WSL: Windows node.exe reachable at /mnt/c/Program Files/nodejs/node.exe
[PASS] WSL: TV_MCP_WIN_REPO points to valid Windows clone (C:\Users\jose\wally-trader)
```

### Step W3 — Telegram bot

```bash
make hermes-telegram-setup   # interactive: token → chat_id auto → confirmation
```

### Step W4 — Run as systemd-user service

```bash
make hermes-systemd-install   # copies unit, daemon-reload, enable --now

# Survive logout / WSL shell exit:
loginctl enable-linger $USER

# Verify:
systemctl --user status hermes
journalctl --user -u hermes -f    # live logs
make hermes-logs                  # alternative: tails logs/hermes-daemon.log
```

To restart after editing config:

```bash
make hermes-restart   # auto-detects systemd vs launchd
```

### WSL troubleshooting

**`/proc/sys/kernel/osrelease` doesn't say microsoft/wsl** — you're not on WSL2.
The bridge defensively refuses to run; verify with `cat /proc/sys/kernel/osrelease`.

**`node.exe` returns "module not found"** — the Windows-side `tradingview-mcp/`
folder is missing or has no `node_modules/`. Run `npm install` inside
`C:\Users\<you>\wally-trader\tradingview-mcp\` from Windows PowerShell, not WSL.

**TV MCP starts but draws nothing** — TradingView Desktop must be open and
focused on the symbol you're trying to draw on (`BINANCE:BTCUSDT.P` for retail,
`BINGX:BTCUSDT.P` for retail-bingx, etc.). The MCP attaches via CDP to the
running TV Electron process; if TV is closed or on a different ticker, drawing
tools fail silently.

**systemd-user not available (`Failed to connect to bus`)** — your WSL doesn't
have systemd enabled. Edit `/etc/wsl.conf`:

```ini
[boot]
systemd=true
```

Then `wsl --shutdown` from Windows PowerShell and re-open the WSL shell.

**Daemon stops when you close the WSL shell** — you didn't enable lingering:
`loginctl enable-linger $USER`. Without this, systemd-user tears down when
your last login session ends.

**Need different paths than the wrapper auto-detects** — set in `~/wally-trader/.env`:

```bash
HERMES_SUBCMD=serve   # force the subcommand if --help parsing fails
WIN_NODE_EXE=/mnt/c/Tools/node-v20/node.exe   # nvm-windows custom path
```

The wrapper sources `.env` before exec'ing hermes, so any override applies
on next `make hermes-restart`.

---

## Cross-device caveat

This setup ties all MCP tool execution to **your Mac being awake and running**.

If your Mac:
- **Sleeps** → Telegram bot stops responding (configure "prevent sleep" above)
- **Reboots** → daemon restarts automatically via launchd, but takes ~30s
- **Loses internet** → Telegram polling disconnects; daemon reconnects automatically

For 100% uptime: dedicate a Mac mini as an always-on Hermes host. Same setup,
just point TradingView MCP at a Mac mini running TV Desktop in screen share mode.

---

## Files reference

| File | Purpose |
|---|---|
| `adapters/hermes/install.sh` | One-command setup (skills + symlink + MCPs + chmod helpers) |
| `adapters/hermes/configure_mcp.sh` | MCP registration (idempotent, WSL-aware via `platform_overrides`) |
| `adapters/hermes/transform.py` | Converts `system/` → `.hermes/skills/` |
| `adapters/hermes/hermes_daemon_wrapper.sh` | Launched by launchd/systemd. Auto-detects hermes binary + subcommand, sources `.env`, rotates logs |
| `adapters/hermes/wsl_tv_bridge.sh` | WSL-only: exec's `node.exe` against the Windows-side tradingview-mcp |
| `adapters/hermes/telegram_setup.sh` | Interactive Telegram bootstrap (token + chat_id auto-discovery) |
| `scripts/hermes_smoke.sh` | Smoke test, 6 base + 3 WSL-only checks |
| `.claude/launchd/com.wally.hermes-daemon.plist` | launchd plist for daemon (macOS) |
| `.claude/systemd/hermes.service` | systemd-user unit (Linux/WSL) |
| `system/mcp/servers.json` | Canonical MCP server definitions (with `platform_overrides`) |
| `.env` | Local secrets / per-machine overrides (`TV_MCP_WIN_REPO`, `WIN_NODE_EXE`, `HERMES_SUBCMD`, `NOTION_API_KEY`) |
| `logs/hermes-daemon.log` | Daemon stdout+stderr (created at runtime, rotated by wrapper) |
