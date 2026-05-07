"""chainlink_check tool — cross-check price against Chainlink oracle via existing script."""
import json
import subprocess
from pathlib import Path


def chainlink_check(symbol: str, current_price: float | None = None) -> dict:
    """Run chainlink_price script and parse output.

    The existing scripts live at .claude/scripts/chainlink_price.{py,sh} in the repo root.

    Args:
        symbol: asset symbol (e.g. "BTC")
        current_price: optional exchange price to compare against oracle

    Returns: parsed JSON from the script, or {"error": ..., "symbol": ...}
    """
    # Walk up from this file to the repo root (5 levels: tools/ → wally_trader_mcp/ → src/ → wally-trader-mcp/ → worktrees/ → repo)
    repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent
    script_py = repo_root / ".claude" / "scripts" / "chainlink_price.py"
    script_sh = repo_root / ".claude" / "scripts" / "chainlink_price.sh"

    if script_py.exists():
        cmd = ["python3", str(script_py), symbol]
    elif script_sh.exists():
        cmd = ["bash", str(script_sh), symbol]
    else:
        return {"error": "chainlink script not found", "symbol": symbol}

    if current_price is not None:
        cmd += ["--compare", str(current_price)]
    cmd.append("--json")

    try:
        out = subprocess.check_output(cmd, text=True, timeout=30)
        return json.loads(out)
    except subprocess.TimeoutExpired:
        return {"error": "timeout", "symbol": symbol}
    except (json.JSONDecodeError, subprocess.CalledProcessError) as e:
        return {"error": str(e), "symbol": symbol}
