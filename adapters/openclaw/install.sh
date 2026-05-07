#!/usr/bin/env bash
# adapters/openclaw/install.sh
# First-time setup: generate .openclaw/skills/, symlink to ~/.openclaw/skills/wally-trader/,
# install git pre-commit hook for auto-sync.

set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO"

# Verify Python 3 + pyyaml available
python3 -c "import yaml" 2>/dev/null || {
  echo "⚠️  PyYAML not installed. Installing..."
  pip3 install --user pyyaml
}

# First generation
echo "🔄 Generating .openclaw/skills/ from system/..."
USE_OR=""
if [[ "${WALLY_USE_OPENROUTER:-0}" == "1" ]]; then
  USE_OR="--openrouter"
fi
python3 "$REPO/adapters/openclaw/transform.py" $USE_OR

# Symlink to ~/.openclaw/skills/wally-trader/ if OpenClaw is installed
OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/.openclaw}"
OPENCLAW_SKILLS="$OPENCLAW_HOME/skills"
LINK="$OPENCLAW_SKILLS/wally-trader"
TARGET="$REPO/.openclaw/skills"

if [ -d "$OPENCLAW_HOME" ]; then
  mkdir -p "$OPENCLAW_SKILLS"
  if [ -L "$LINK" ]; then
    if [ "$(readlink "$LINK")" != "$TARGET" ]; then
      rm "$LINK"
      ln -s "$TARGET" "$LINK"
      echo "✓ Updated symlink $LINK → $TARGET"
    else
      echo "✓ Symlink $LINK → $TARGET already correct"
    fi
  elif [ -e "$LINK" ]; then
    BACKUP="$LINK.backup-$(date +%s)"
    mv "$LINK" "$BACKUP"
    ln -s "$TARGET" "$LINK"
    echo "✓ Backed up existing $LINK → $BACKUP and created symlink"
  else
    ln -s "$TARGET" "$LINK"
    echo "✓ Created symlink $LINK → $TARGET"
  fi
else
  echo "ℹ️  OpenClaw not installed yet ($OPENCLAW_HOME missing). Skipping symlink."
  echo "   Install OpenClaw: see https://openclaw.dev for installation instructions."
  echo "   Then re-run this install.sh to create the symlink."
fi

# Install git pre-commit hook (use rev-parse for worktree compat)
HOOK_PATH="$(git rev-parse --git-path hooks/pre-commit)"
HOOK_DIR="$(dirname "$HOOK_PATH")"
mkdir -p "$HOOK_DIR"

MARKER='# openclaw-adapter-v1'

if [ -f "$HOOK_PATH" ] && grep -q "$MARKER" "$HOOK_PATH"; then
  echo "✓ pre-commit hook already installed (openclaw v1)"
else
  if [ -f "$HOOK_PATH" ]; then
    cp "$HOOK_PATH" "$HOOK_PATH.backup-$(date +%s)"
    echo "   Backed up existing pre-commit to $HOOK_PATH.backup-*"
  fi

  cat >> "$HOOK_PATH" <<'EOF'

# openclaw-adapter-v1 — auto-regenerate .openclaw/skills/ on system/ changes
__REPO="$(git rev-parse --show-toplevel)"
__CHANGED=$(git diff --cached --name-only | grep -E '^system/(commands|agents)/' || true)
if [ -n "$__CHANGED" ]; then
  echo "[openclaw-adapter] system/ changed → re-generando .openclaw/skills/"
  python3 "$__REPO/adapters/openclaw/transform.py" || exit 1
  git add "$__REPO/.openclaw"
fi
EOF
  chmod +x "$HOOK_PATH"
  echo "✓ pre-commit hook installed at $HOOK_PATH"
fi

echo ""
echo "✅ OpenClaw adapter ready."
echo "   .openclaw/skills/ will auto-regenerate on git commit when system/ changes."
echo ""
echo "📋 Next steps:"
echo "   1. Install OpenClaw (if not yet): see https://openclaw.dev for installation instructions"
echo "   2. openclaw setup    # configure model + provider"
echo "   3. openclaw          # start interactive CLI (auto-loads AGENTS.md + skills)"
echo ""
echo "💡 Configure TradingView MCP (optional):"
echo "   openclaw config set mcp.tradingview.command node"
echo "   openclaw config set mcp.tradingview.args '[\"$REPO/tradingview-mcp/src/server.js\"]'"
