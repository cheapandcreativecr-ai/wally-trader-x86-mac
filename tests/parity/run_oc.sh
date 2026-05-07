#!/usr/bin/env bash
# Run an OpenClaw prompt non-interactive, capture stdout
# Usage: run_oc.sh <profile> <prompt>
set -euo pipefail
PROFILE="${1:-bitunix}"
PROMPT="${2:-/help}"
WALLY_PROFILE="$PROFILE" openclaw agent --message "$PROMPT" --json 2>/dev/null
