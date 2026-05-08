#!/usr/bin/env bash
# .claude/scripts/profile.sh — bash wrapper for profile.py (canonical implementation)
#
# Usage:
#   profile.sh show        — prints current profile (env var WALLY_PROFILE overrides file)
#   profile.sh get         — prints just the profile name (no timestamp)
#   profile.sh set <name>  — switches to <name> (retail|ftmo|fotmarkets|...)
#   profile.sh stale       — exits 0 if stale >12h, exits 1 otherwise
#   profile.sh validate    — checks profile exists in profiles/ dir
#
# Multi-terminal mode:
#   Set WALLY_PROFILE env var per-terminal to use different profiles in parallel.
#
# Cross-platform:
#   - macOS/Linux: this bash wrapper, calls python3
#   - Windows:     use .claude/scripts/win/profile.cmd or profile.ps1 (which call python)
#   - Both:        delegate to .claude/scripts/profile.py (canonical Python implementation)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_SCRIPT="$SCRIPT_DIR/profile.py"

# Prefer python3 on macOS/Linux; fallback to python (Windows-style if running under Git Bash)
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "ERROR: Python 3 not found in PATH. Install via: brew install python3 (macOS) | apt install python3 (Linux) | python.org (Windows)" >&2
  exit 99
fi

export WALLY_PROFILE=retail-bingx
exec "$PY" "$PY_SCRIPT" "$@"
