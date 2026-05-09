#!/usr/bin/env bash
# adapters/hermes/telegram_setup.sh
#
# Interactive bootstrap for Hermes' Telegram bot. Replaces the manual
# `curl … getUpdates | grep id` ritual from docs/hermes-setup.md Step 3.
#
# What it does
# ────────────
#   1. Prompts for a bot token (from @BotFather), validates with /getMe.
#   2. Saves token via `hermes config set telegram.bot_token`.
#   3. Asks the user to message the bot.
#   4. Polls /getUpdates for up to 90s, extracts the chat_id automatically.
#   5. Saves chat_id via `hermes config set telegram.allowed_chat_ids '[ID]'`.
#   6. Sends a confirmation message to that chat so the user sees the loop is closed.
#
# Idempotent: re-running with the same token + chat_id is a no-op apart from
# resending the confirmation message.
#
# Usage:
#   make hermes-telegram-setup
#   bash adapters/hermes/telegram_setup.sh         # direct
#   bash adapters/hermes/telegram_setup.sh <token> # skip token prompt

set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"

# ── Sanity: hermes on PATH ───────────────────────────────────────────────────
if ! command -v hermes >/dev/null 2>&1; then
  echo "❌  hermes not on PATH. Install Hermes first:" >&2
  echo "    curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash" >&2
  exit 1
fi

# Sanity: curl present
if ! command -v curl >/dev/null 2>&1; then
  echo "❌  curl is required." >&2
  exit 1
fi

echo "═════════════════════════════════════════════════════════════"
echo "   Hermes Telegram bot setup"
echo "═════════════════════════════════════════════════════════════"
echo ""

# ── Step 1: bot token ────────────────────────────────────────────────────────
TOKEN="${1:-}"
if [ -z "$TOKEN" ]; then
  echo "1️⃣  Create a bot:"
  echo "    • Open Telegram → search @BotFather → /newbot"
  echo "    • Copy the token (looks like 7123456789:AAF…)"
  echo ""
  read -r -p "Paste bot token: " TOKEN
fi
TOKEN="${TOKEN// /}"  # trim whitespace
if [ -z "$TOKEN" ]; then
  echo "❌  Empty token. Aborting." >&2
  exit 1
fi
if ! [[ "$TOKEN" =~ ^[0-9]+:[A-Za-z0-9_-]+$ ]]; then
  echo "⚠️   Token doesn't match expected format (NNN:LETTERS_AND_DIGITS)." >&2
  echo "    Continuing anyway, but /getMe will validate." >&2
fi

echo ""
echo "🔍  Validating token via Telegram /getMe …"
GET_ME="$(curl -sS --max-time 10 "https://api.telegram.org/bot${TOKEN}/getMe" || true)"
if ! echo "$GET_ME" | grep -q '"ok":true'; then
  echo "❌  Telegram rejected the token. Response:" >&2
  echo "$GET_ME" >&2
  exit 1
fi
BOT_USER="$(echo "$GET_ME" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['result']['username'])" 2>/dev/null || echo unknown)"
echo "✅  Token valid → bot is @${BOT_USER}"

echo ""
echo "💾  Saving token via hermes config set telegram.bot_token …"
hermes config set telegram.bot_token "$TOKEN" >/dev/null
echo "✅  Token saved."

# ── Step 2: discover chat_id ─────────────────────────────────────────────────
echo ""
echo "2️⃣  Open Telegram and send ANY message to @${BOT_USER}"
echo "    (e.g. say 'hi' or '/start')"
echo ""
echo "    Waiting for your message …"

CHAT_ID=""
DEADLINE=$(( $(date +%s) + 90 ))
ATTEMPT=0
while [ "$(date +%s)" -lt "$DEADLINE" ]; do
  ATTEMPT=$((ATTEMPT + 1))
  UPDATES="$(curl -sS --max-time 8 "https://api.telegram.org/bot${TOKEN}/getUpdates?limit=10&timeout=5" || true)"
  CHAT_ID="$(echo "$UPDATES" | python3 - <<'PY' 2>/dev/null || true
import sys, json
try:
    d = json.load(sys.stdin)
    for upd in reversed(d.get("result", [])):
        msg = upd.get("message") or upd.get("edited_message") or upd.get("channel_post")
        if msg and "chat" in msg and "id" in msg["chat"]:
            print(msg["chat"]["id"])
            break
except Exception:
    pass
PY
)"
  if [ -n "$CHAT_ID" ]; then
    break
  fi
  printf "    [attempt %d] no message yet, retrying in 5s…\r" "$ATTEMPT"
  sleep 5
done
echo ""

if [ -z "$CHAT_ID" ]; then
  echo "❌  Timed out waiting 90s for a Telegram message." >&2
  echo "    Did you send a message to @${BOT_USER}? Re-run when ready." >&2
  exit 1
fi
echo "✅  Got chat_id: $CHAT_ID"

# ── Step 3: allowlist ────────────────────────────────────────────────────────
echo ""
echo "💾  Saving allowlist via hermes config set telegram.allowed_chat_ids …"
hermes config set telegram.allowed_chat_ids "[${CHAT_ID}]" >/dev/null
echo "✅  Allowlist saved."

# ── Step 4: confirmation message ─────────────────────────────────────────────
echo ""
echo "📨  Sending confirmation message …"
HOST_NAME="$(hostname 2>/dev/null || echo unknown-host)"
TS="$(date '+%Y-%m-%d %H:%M:%S %Z')"
MSG="✅ Hermes connected
host: ${HOST_NAME}
time: ${TS}
You can now send commands like /status or /punk-hunt"
SEND_RESP="$(curl -sS --max-time 10 \
  -d "chat_id=${CHAT_ID}" \
  --data-urlencode "text=${MSG}" \
  "https://api.telegram.org/bot${TOKEN}/sendMessage" || true)"
if echo "$SEND_RESP" | grep -q '"ok":true'; then
  echo "✅  Confirmation sent. Check Telegram."
else
  echo "⚠️   sendMessage failed (allowlist saved anyway). Response:"
  echo "$SEND_RESP"
fi

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "═════════════════════════════════════════════════════════════"
echo "  All done. Next steps:"
echo "    • macOS:  make hermes-daemon-install"
echo "    • Linux/WSL: make hermes-systemd-install"
echo "    • Then: send /status from Telegram"
echo "═════════════════════════════════════════════════════════════"
