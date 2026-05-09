# Hermes Quickstart — 5 commands to enable Telegram to TradingView remote

## Prerequisites
- Mac stays on with TradingView Desktop logged in
- Telegram bot token from @BotFather
- Your Telegram chat ID (send a message to your bot, check https://api.telegram.org/bot<TOKEN>/getUpdates)

## 5 commands

```bash
# 1. Install Hermes daemon
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

# 2. Setup wally-trader skills + MCPs
make hermes-install

# 3. Configure Telegram bot
hermes config set telegram.bot_token "YOUR_TOKEN_HERE"
hermes config set telegram.allowed_chat_ids '["YOUR_CHAT_ID"]'

# 4. Verify smoke test (6 checks)
make hermes-smoke

# 5. Install daemon (always-on via launchd)
make hermes-daemon-install
```

## Test it

From Telegram, send to your bot: `/regime`
Expected response within 30s.

Then: `/chart` → TradingView Desktop on your Mac redraws current setup.

## Commands available remotely

| Telegram command | Description |
|---|---|
| `/regime` | Detect current market regime (ADX + DI) |
| `/status` | Show profile status + open trades |
| `/punk-morning` | Pre-session bitunix scan |
| `/punk-hunt` | Hunt for best setup now |
| `/signal SYMBOL SIDE entry sl=X tp=Y` | Validate a signal |
| `/chart` | Redraw current TV chart with levels |
| `/cushion --day-realized X --position-pnl Y --liq-distance-pct Z --capital N` | Cushion-aware hold/cut decision |

## Troubleshooting

- Bot not responding: `launchctl list | grep hermes` should show running. Check `tail -f logs/hermes-daemon.log`.
- TV drawing fails: ensure TradingView Desktop is open + on the right symbol/chart.
- Permission error: ensure your Telegram chat ID is in `allowed_chat_ids`.
- Skills not found: run `make hermes-install` to regenerate skill registry.

## Cross-device workflow

1. Mac at home: Hermes daemon always-on → processes Telegram commands → executes MCP tools against TradingView Desktop
2. iPhone Telegram: you send commands while away from desk
3. Bitunix mobile app: you execute trades manually after Hermes delivers analysis

This lets you manage open positions (check cushion, watch trade context) from anywhere without opening your laptop.

## Windows + WSL2 Ubuntu setup

The wally-trader system supports running Hermes on Windows via WSL2 Ubuntu, sharing state with macOS via Notion memory backend.

### Prerequisites (Windows side)
- Windows 10/11 with WSL2 enabled
- Ubuntu distro installed (`wsl --install -d Ubuntu` from PowerShell)
- systemd enabled in WSL2 (`/etc/wsl.conf` with `[boot]\nsystemd=true`)
- TradingView Desktop on Windows (optional, only if you want `/chart` from Telegram drawing remotely)

### Quick install (5 minutes from inside WSL Ubuntu)

```bash
# 1. Clone repo
git clone https://github.com/sasasamaes/wally-trader.git && cd wally-trader

# 2. Run automated setup (asks for NOTION_API_KEY)
bash scripts/setup-windows-wsl.sh

# 3. Configure Telegram bot
hermes config set telegram.bot_token "BOT_TOKEN_FROM_BOTFATHER"
hermes config set telegram.allowed_chat_ids '[YOUR_CHAT_ID]'

# 4. Install systemd daemon (script printed the exact recipe)
# Copy/paste from script output

# 5. Test
make hermes-smoke
# Send /regime from Telegram to your bot
```

### Cross-OS state sync

The HybridBackend writes locally first, then async-mirrors to Notion. Both machines (macOS + Windows) point to the same Notion workspace via shared NOTION_API_KEY.

When switching machines:
```bash
# On Windows when starting work:
make sync-pull PROFILE=bitunix
# Refreshes local cache from Notion before any new writes
```

### TradingView Desktop limitation

The TV MCP server only controls the local TradingView Desktop instance:
- If TV Desktop is on Mac only → `/chart` works only when invoking from Mac
- If TV Desktop is also on Windows → install TradingView for Windows (free, same login), then `/chart` works from Telegram via Hermes daemon

**Recommended:** install TV Desktop on both. Layouts sync via TV cloud automatically.

### Common issues

- **systemd not enabled**: edit `/etc/wsl.conf`, add `[boot]\nsystemd=true`, then `wsl --shutdown` from PowerShell
- **`make: command not found`**: `sudo apt install make`
- **`hermes: command not found`**: re-run their installer; check PATH includes `~/.local/bin`
- **NOTION_API_KEY not persisting**: confirm it's exported in `~/.bashrc` (the script handles this)
- **Telegram bot not responding**: check `systemctl --user status wally-hermes` + `tail -f logs/hermes-daemon.log`
