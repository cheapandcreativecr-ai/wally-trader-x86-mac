#!/usr/bin/env bash
# adapters/hermes/wsl_tv_bridge.sh
#
# Cross-OS bridge for the TradingView MCP when Hermes runs in WSL Ubuntu and
# TradingView Desktop runs in Windows native.
#
# Why this script exists
# ──────────────────────
# TradingView Desktop is Windows-only and the tradingview-mcp attaches to it
# via the Chrome DevTools Protocol on localhost. So node.exe MUST run on the
# Windows side. WSL2's Linux↔Windows interop layer lets us:
#   1. Invoke /mnt/c/Program Files/nodejs/node.exe directly from bash
#   2. Pipe stdin/stdout transparently across the boundary (this is what
#      stdio MCP transport needs)
#
# This script is what `system/mcp/servers.json` registers as the tradingview
# command on WSL via the `platform_overrides.wsl` entry. configure_mcp.sh
# detects WSL and routes the registration through here.
#
# Required env (with sensible defaults)
# ─────────────────────────────────────
#   WIN_NODE_EXE        — Windows path to node.exe, in WSL (/mnt/c/...) form
#                         Default: /mnt/c/Program Files/nodejs/node.exe
#   TV_MCP_WIN_REPO     — Windows path to the Windows-side wally-trader clone,
#                         in Windows form (e.g. C:\Users\jose\wally-trader).
#                         REQUIRED — no default. node.exe needs a Windows-style
#                         path to resolve server.js and its node_modules cache.
#
# Optional:
#   TV_MCP_WIN_SERVER_REL — relative path inside the Windows repo to server.js
#                           Default: tradingview-mcp\src\server.js
#
# These are sourced from $REPO/.env if present (loaded by hermes_daemon_wrapper.sh
# or by the user's shell). For one-off testing, prefix the env inline:
#   TV_MCP_WIN_REPO='C:\wally-trader' bash adapters/hermes/wsl_tv_bridge.sh
#
# Failure modes
# ─────────────
#   1 — not running on WSL (defensive; this script is WSL-only)
#   2 — node.exe not found at WIN_NODE_EXE
#   3 — TV_MCP_WIN_REPO env var unset
#
# After exec, the process IS node.exe — Hermes/MCP stdio flows directly.

set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"

# ── Source .env so users can keep TV_MCP_WIN_REPO in $REPO/.env ──────────────
if [ -f "$REPO/.env" ]; then
  # shellcheck disable=SC1091
  set -a; . "$REPO/.env"; set +a
fi

# ── Defensive: refuse to run outside WSL ─────────────────────────────────────
# /proc/sys/kernel/osrelease contains "microsoft" or "WSL" on WSL kernels.
if ! grep -qiE 'microsoft|wsl' /proc/sys/kernel/osrelease 2>/dev/null; then
  echo "[wsl_tv_bridge] ERROR: this script only runs on WSL." >&2
  echo "                 osrelease=$(cat /proc/sys/kernel/osrelease 2>/dev/null || echo n/a)" >&2
  echo "                 On macOS/Linux native, configure_mcp.sh wires tradingview directly to node." >&2
  exit 1
fi

# ── Validate Windows-side node.exe ───────────────────────────────────────────
WIN_NODE_EXE="${WIN_NODE_EXE:-/mnt/c/Program Files/nodejs/node.exe}"
if [ ! -x "$WIN_NODE_EXE" ]; then
  echo "[wsl_tv_bridge] ERROR: node.exe not found or not executable at:" >&2
  echo "                   $WIN_NODE_EXE" >&2
  echo "                 Install Node.js on Windows (https://nodejs.org → MSI) or" >&2
  echo "                 set WIN_NODE_EXE in $REPO/.env to the WSL-style path:" >&2
  echo "                   WIN_NODE_EXE=/mnt/c/Path/To/node.exe" >&2
  exit 2
fi

# ── Resolve Windows-side server.js path ──────────────────────────────────────
TV_MCP_WIN_REPO="${TV_MCP_WIN_REPO:-}"
if [ -z "$TV_MCP_WIN_REPO" ]; then
  echo "[wsl_tv_bridge] ERROR: TV_MCP_WIN_REPO is unset." >&2
  echo "                 Add to $REPO/.env (Windows-style path, no quotes):" >&2
  echo '                   TV_MCP_WIN_REPO=C:\Users\jose\wally-trader' >&2
  echo "                 (the Windows clone of this repo, where TV MCP runs)" >&2
  exit 3
fi

TV_MCP_WIN_SERVER_REL="${TV_MCP_WIN_SERVER_REL:-tradingview-mcp\\src\\server.js}"
# Concatenate as Windows path (use \\ between repo and rel)
WIN_SERVER_PATH="${TV_MCP_WIN_REPO%\\}\\${TV_MCP_WIN_SERVER_REL#\\}"

# Quick reachability check: convert the Windows path to a /mnt/c/... form so
# we can `test -f` it from WSL. wslpath is the canonical translator.
if command -v wslpath >/dev/null 2>&1; then
  WSL_VIEW_OF_SERVER="$(wslpath -u "$WIN_SERVER_PATH" 2>/dev/null || true)"
  if [ -n "$WSL_VIEW_OF_SERVER" ] && [ ! -f "$WSL_VIEW_OF_SERVER" ]; then
    echo "[wsl_tv_bridge] WARNING: server.js not visible from WSL at:" >&2
    echo "                   $WSL_VIEW_OF_SERVER" >&2
    echo "                 (Windows path: $WIN_SERVER_PATH)" >&2
    echo "                 node.exe will fail. Verify TV_MCP_WIN_REPO and that the" >&2
    echo "                 Windows-side clone has tradingview-mcp/ checked out." >&2
    # Don't exit — let node.exe report its own error in case we mis-translated.
  fi
fi

# Also CD to the Windows-side repo so node resolves node_modules from the
# correct location. cd needs the WSL-mapped path.
WIN_REPO_WSL=""
if command -v wslpath >/dev/null 2>&1; then
  WIN_REPO_WSL="$(wslpath -u "$TV_MCP_WIN_REPO" 2>/dev/null || true)"
fi
if [ -n "$WIN_REPO_WSL" ] && [ -d "$WIN_REPO_WSL/tradingview-mcp" ]; then
  cd "$WIN_REPO_WSL/tradingview-mcp"
fi

# ── Exec node.exe ────────────────────────────────────────────────────────────
# stderr to stderr (Hermes/MCP framing is on stdout, so anything we print
# above goes to logs cleanly). exec replaces the shell so the MCP child
# tree is just node.exe — no orphan bash hanging around.
exec "$WIN_NODE_EXE" "$WIN_SERVER_PATH"
