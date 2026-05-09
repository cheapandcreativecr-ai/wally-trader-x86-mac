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
