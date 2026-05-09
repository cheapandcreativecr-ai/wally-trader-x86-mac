#!/usr/bin/env bash
# adapters/hermes/hermes_daemon_wrapper.sh
#
# Wrapper invoked by launchd (macOS) or systemd-user (Linux/WSL) instead of
# calling `/usr/local/bin/hermes serve` directly. Solves the portability
# issues that made the plist/unit fragile across machines:
#
#   1. Auto-detects the hermes binary (Homebrew on Apple Silicon lives at
#      /opt/homebrew/bin/hermes, Intel/manual installs at /usr/local/bin/hermes,
#      personal installs at ~/.hermes/bin/hermes). PATH is searched in order.
#   2. Auto-detects the daemon subcommand by parsing `hermes --help` so a
#      future Hermes that renames `serve` → `daemon` (or whatever) keeps
#      working without editing the plist.
#   3. Sources $REPO/.env if present so secrets like NOTION_API_KEY reach
#      the MCP children that hermes spawns.
#   4. Rotates logs/hermes-daemon.log when it grows past 10 MB. launchd
#      restarts the wrapper on every daemon restart so this rotation runs
#      organically without an extra cron job.
#
# Exit codes:
#   0 — never (we exec into hermes); if you see a wrapper exit it's an error
#   2 — hermes binary not found
#   3 — could not determine subcommand
#
# This script must remain idempotent and crash-loop-safe: launchd has
# ThrottleInterval=30s, but if we exit fast every time we still spam logs.

set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
LOG_FILE="$REPO/logs/hermes-daemon.log"
LOG_MAX_BYTES=$((10 * 1024 * 1024))  # 10 MB

# ── 1. Source .env if present (NOTION_API_KEY, TELEGRAM token overrides, etc.)
if [ -f "$REPO/.env" ]; then
  # shellcheck disable=SC1091
  set -a; . "$REPO/.env"; set +a
  echo "[wrapper] sourced $REPO/.env"
fi

# ── 2. Locate hermes binary ──────────────────────────────────────────────────
# Build a candidate list and pick the first that exists. We keep PATH-based
# lookup last so user-set PATH wins after explicit candidates.
CANDIDATES=(
  "$HOME/.hermes/bin/hermes"          # universal (Hermes installer default)
  "$HOME/.local/bin/hermes"           # common on Linux/WSL pipx-style installs
  "/opt/homebrew/bin/hermes"          # macOS Apple Silicon Homebrew
  "/usr/local/bin/hermes"             # macOS Intel / Linux manual install
  "/usr/bin/hermes"                   # Linux distro packages
)
HERMES_BIN=""
for c in "${CANDIDATES[@]}"; do
  if [ -x "$c" ]; then HERMES_BIN="$c"; break; fi
done
# Fallback: PATH lookup (covers exotic installs the candidates miss)
if [ -z "$HERMES_BIN" ] && command -v hermes >/dev/null 2>&1; then
  HERMES_BIN="$(command -v hermes)"
fi

if [ -z "$HERMES_BIN" ]; then
  echo "[wrapper] ERROR: hermes binary not found. Searched:" >&2
  printf '   %s\n' "${CANDIDATES[@]}" >&2
  echo "   PATH=$PATH" >&2
  echo "   Install: curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash" >&2
  exit 2
fi
echo "[wrapper] using hermes binary: $HERMES_BIN"

# ── 3. Detect daemon subcommand ──────────────────────────────────────────────
# Parse `hermes --help` and pick the first matching subcommand. Order matters:
# `serve` is the v0.x default, `bot` and `daemon` are common renames, `run`
# is the catch-all. If override is set via $HERMES_SUBCMD env, trust it.
SUBCMD="${HERMES_SUBCMD:-}"
if [ -z "$SUBCMD" ]; then
  HELP="$("$HERMES_BIN" --help 2>&1 || true)"
  for candidate in serve bot daemon run start; do
    if echo "$HELP" | grep -qE "(^|[[:space:]])${candidate}([[:space:]]|$)"; then
      SUBCMD="$candidate"; break
    fi
  done
fi
if [ -z "$SUBCMD" ]; then
  echo "[wrapper] ERROR: could not detect a daemon subcommand from \`$HERMES_BIN --help\`." >&2
  echo "   Set HERMES_SUBCMD env var to override (e.g. HERMES_SUBCMD=serve)." >&2
  exit 3
fi
echo "[wrapper] using subcommand: $SUBCMD"

# ── 4. Log rotation (size-based, run-once-per-launch) ────────────────────────
# Rotation only happens when launchd starts/restarts the daemon. For trading
# pace this is plenty; if you need continuous rotation use newsyslog.
if [ -f "$LOG_FILE" ]; then
  SIZE=$(wc -c < "$LOG_FILE" 2>/dev/null || echo 0)
  if [ "$SIZE" -gt "$LOG_MAX_BYTES" ]; then
    STAMP="$(date +%Y%m%d-%H%M%S)"
    ROTATED="${LOG_FILE}.${STAMP}.gz"
    gzip -c "$LOG_FILE" > "$ROTATED" 2>/dev/null || true
    : > "$LOG_FILE"   # truncate in place; launchd's open fd keeps writing
    echo "[wrapper] rotated log → $(basename "$ROTATED")"
    # Keep only last 10 rotated logs
    ls -1t "${LOG_FILE}".*.gz 2>/dev/null | tail -n +11 | xargs -I{} rm -f {} || true
  fi
fi

# ── 5. Exec into hermes ──────────────────────────────────────────────────────
cd "$REPO"
echo "[wrapper] $(date '+%Y-%m-%d %H:%M:%S') exec → $HERMES_BIN $SUBCMD"
exec "$HERMES_BIN" "$SUBCMD"
