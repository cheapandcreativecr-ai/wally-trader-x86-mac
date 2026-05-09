#!/usr/bin/env bash
# adapters/hermes/configure_mcp.sh
# Idempotent: reads system/mcp/servers.json and registers each server in Hermes config.
# Safe to re-run at any time. Skips silently if hermes is not on PATH.
#
# Usage:
#   bash adapters/hermes/configure_mcp.sh
#   (also called automatically by adapters/hermes/install.sh)

set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
SERVERS_JSON="$REPO/system/mcp/servers.json"

# ── Hermes availability check ─────────────────────────────────────────────────
if ! command -v hermes >/dev/null 2>&1; then
  echo "ℹ️  hermes not found on PATH — skipping MCP registration."
  echo "   Install Hermes first, then re-run: bash adapters/hermes/configure_mcp.sh"
  exit 0
fi

# ── Verify jq or python3 available for JSON parsing ───────────────────────────
if command -v python3 >/dev/null 2>&1; then
  JSON_TOOL="python3"
elif command -v jq >/dev/null 2>&1; then
  JSON_TOOL="jq"
else
  echo "❌  Neither python3 nor jq found — cannot parse servers.json. Aborting."
  exit 1
fi

# ── Helper: expand ${VAR} placeholders in a string using current env ──────────
expand_env_placeholders() {
  local input="$1"
  # Use python3 to substitute ${VAR} → actual value, warn on missing
  python3 - "$input" "$REPO" <<'PYEOF'
import sys, os, re

value = sys.argv[1]
repo  = sys.argv[2]

# Substitute ${REPO} → actual repo path first (internal placeholder)
value = value.replace("${REPO}", repo)

def replacer(m):
    var = m.group(1)
    env_val = os.environ.get(var)
    if env_val is None:
        print(f"  ⚠️  env var ${{{var}}} is unset — keeping literal placeholder", file=sys.stderr)
        return m.group(0)
    return env_val

result = re.sub(r'\$\{([^}]+)\}', replacer, value)
print(result, end='')
PYEOF
}

# ── Parse servers.json with python3 ───────────────────────────────────────────
echo "📡 Registering MCP servers in Hermes config..."
echo "   Source: $SERVERS_JSON"

python3 - "$SERVERS_JSON" "$REPO" <<'PYEOF'
import sys, os, json, subprocess, re, platform

servers_path = sys.argv[1]
repo         = sys.argv[2]

with open(servers_path) as f:
    data = json.load(f)

servers = data.get("servers", {})

# ── Platform detection ────────────────────────────────────────────────────────
# We expose three buckets for platform_overrides: "wsl", "macos", "linux".
# WSL is detected by looking for "microsoft" or "wsl" in /proc/sys/kernel/osrelease,
# which is the canonical signal (works across WSL1/WSL2 and any distro).
def detect_platform() -> str:
    osrel = ""
    try:
        with open("/proc/sys/kernel/osrelease") as f:
            osrel = f.read().lower()
    except FileNotFoundError:
        pass
    if "microsoft" in osrel or "wsl" in osrel:
        return "wsl"
    sysname = platform.system().lower()
    if sysname == "darwin":
        return "macos"
    return "linux"

PLATFORM = detect_platform()
print(f"  🖥  detected platform: {PLATFORM}")

def apply_platform_override(name: str, cfg: dict) -> dict:
    """If the server defines platform_overrides[PLATFORM], shallow-merge it on top."""
    overrides = cfg.get("platform_overrides", {})
    pov = overrides.get(PLATFORM)
    if not pov:
        return cfg
    merged = dict(cfg)
    # Shallow merge: override fields replace top-level. Nested dicts (env) merged.
    for k, v in pov.items():
        if k.startswith("$"):  # skip $comment etc
            continue
        if k == "env" and isinstance(v, dict):
            merged_env = dict(merged.get("env", {}))
            merged_env.update(v)
            merged[k] = merged_env
        else:
            merged[k] = v
    print(f"     ↳ {name}: applied platform_overrides[{PLATFORM}]")
    return merged

def expand_env(value: str) -> str:
    """Expand ${VAR} → env value. Warn if unset, keep literal."""
    value = value.replace("<repo>", repo).replace("${REPO}", repo)
    def sub(m):
        var = m.group(1)
        env_val = os.environ.get(var)
        if env_val is None:
            print(f"  ⚠️  env var ${{{var}}} is unset — keeping literal placeholder", file=sys.stderr)
            return m.group(0)
        return env_val
    return re.sub(r'\$\{([^}]+)\}', sub, value)

def hermes_set(key: str, value: str):
    result = subprocess.run(
        ["hermes", "config", "set", key, value],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  ❌  hermes config set {key} failed: {result.stderr.strip()}", file=sys.stderr)
        return False
    return True

ok_count = 0
fail_count = 0

for name, cfg in servers.items():
    if not cfg.get("enabled", True):
        print(f"  ⏭️  {name}: disabled — skipping")
        continue

    print(f"\n  ── {name} ──")
    cfg = apply_platform_override(name, cfg)
    ok = True

    # command
    command = cfg.get("command", "")
    # Resolve relative commands to absolute paths when they look like a path
    if command and not os.path.isabs(command) and "/" in command:
        abs_command = os.path.join(repo, command)
        if os.path.exists(abs_command):
            command = abs_command
    ok &= hermes_set(f"mcp.{name}.command", command)
    print(f"  command: {command}")

    # args — resolve any relative paths inside the args array
    raw_args = cfg.get("args", [])
    resolved_args = []
    for arg in raw_args:
        expanded = expand_env(arg)
        # If it looks like a relative file path, resolve it against repo
        if not os.path.isabs(expanded) and "/" in expanded and not expanded.startswith("-"):
            abs_arg = os.path.join(repo, expanded)
            expanded = abs_arg
        resolved_args.append(expanded)

    args_json = json.dumps(resolved_args)
    ok &= hermes_set(f"mcp.{name}.args", args_json)
    print(f"  args:    {args_json}")

    # cwd — resolve "<repo>" placeholder
    cwd = cfg.get("cwd", "")
    if cwd:
        cwd = cwd.replace("<repo>", repo).replace("${REPO}", repo)
        ok &= hermes_set(f"mcp.{name}.cwd", cwd)
        print(f"  cwd:     {cwd}")
    else:
        # Default cwd to repo root for relative-path commands/args to resolve correctly
        ok &= hermes_set(f"mcp.{name}.cwd", repo)
        print(f"  cwd:     {repo}  (defaulted to repo root)")

    # env — expand ${VAR} placeholders
    env = cfg.get("env", {})
    if env:
        expanded_env = {}
        for k, v in env.items():
            expanded_env[k] = expand_env(str(v))
        env_json = json.dumps(expanded_env)
        ok &= hermes_set(f"mcp.{name}.env", env_json)
        print(f"  env:     {env_json}")

    if ok:
        print(f"  [PASS] {name} registered")
        ok_count += 1
    else:
        print(f"  [FAIL] {name} partially failed — check hermes config manually")
        fail_count += 1

print(f"\n✅ MCP registration complete: {ok_count} ok, {fail_count} failed")
if fail_count > 0:
    sys.exit(1)
PYEOF
