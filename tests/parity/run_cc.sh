#!/usr/bin/env bash
# Run a Claude Code prompt non-interactive, capture stdout
# Usage: run_cc.sh <profile> <prompt>
set -euo pipefail
PROFILE="${1:-bitunix}"
PROMPT="${2:-/help}"
WALLY_PROFILE="$PROFILE" claude --print "$PROMPT" --output-format json 2>/dev/null
