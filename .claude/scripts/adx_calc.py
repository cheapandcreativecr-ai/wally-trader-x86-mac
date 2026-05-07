#!/usr/bin/env python3
"""
ADX(14) + Directional Movement (+DI / -DI) calculator.
Delegates ADX math to wally_core.regime (zero behavior change).

Usage:
    # Pipe OHLCV JSON via stdin:
    cat /tmp/bars.json | python3 .claude/scripts/adx_calc.py

    # Or pass file:
    python3 .claude/scripts/adx_calc.py --file /tmp/bars.json [--length 14]

    # Or quick mode for regime-detector (Bash-friendly):
    python3 .claude/scripts/adx_calc.py --file /tmp/bars.json --quick

Input JSON: list of bars with keys h/high, l/low, c/close (also accepts {bars:[...]} wrapper).

Output (--quick): single line `ADX=<v> +DI=<v> -DI=<v> REGIME=<X>`
Output default: JSON with adx, plus_di, minus_di, last_adx, regime_label, last_close.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

# Auto-inject wally_core from worktree (no venv activation required)
_SHARED = Path(__file__).resolve().parent.parent.parent / "shared/wally_core/src"
if _SHARED.exists() and str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from wally_core.regime import compute_adx  # noqa: E402


def label_regime(adx_val: float, plus_di: float, minus_di: float) -> tuple[str, str]:
    """Map ADX value + DI direction → (regime_label, strategy_recommendation).

    Kept local because wally_core.regime.label_regime returns a simple enum
    without directional suffixes or strategy hints used by this CLI's output.
    """
    direction = "LONG_BIAS" if plus_di > minus_di else "SHORT_BIAS"
    diff = abs(plus_di - minus_di)
    if diff < 2:
        direction = "NEUTRAL"

    if adx_val < 20:
        return "RANGE_CHOP", "Mean Reversion (o NO OPERAR si <15)"
    if adx_val < 25:
        return "TRANSITION", "Cautela: rango terminando o trend incipiente"
    if adx_val < 30:
        return f"TREND_LEVE_{direction}", "Pullback trades en dirección del trend"
    if adx_val < 40:
        return f"TREND_FUERTE_{direction}", "Breakout/Momentum, evitar reversiones"
    return f"TREND_EXTREMO_{direction}", "NO scalping reversal — solo runners trend"


def _normalize_bar(b: dict) -> dict:
    """Normalize h/l/c/o keys to high/low/close/open (wally_core convention)."""
    return {
        "open": float(b.get("open") or b.get("o") or 0),
        "high": float(b.get("high") or b.get("h")),
        "low": float(b.get("low") or b.get("l")),
        "close": float(b.get("close") or b.get("c")),
        "volume": float(b.get("volume") or b.get("v") or 0),
    }


def load_bars(source: str | None) -> list[dict]:
    if source and source != "-":
        with open(source) as f:
            raw = f.read()
    else:
        raw = sys.stdin.read()
    raw = raw.strip()
    if raw.startswith("```"):
        raw = "\n".join(line for line in raw.split("\n") if not line.startswith("```"))
    payload = json.loads(raw)
    if isinstance(payload, dict):
        payload = payload.get("bars") or payload.get("data") or list(payload.values())[0]
    if not isinstance(payload, list):
        raise ValueError("Expected list of bar dicts")
    return payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=None, help="JSON file with bars (default: stdin)")
    ap.add_argument("--length", type=int, default=14)
    ap.add_argument("--quick", action="store_true", help="Single-line output for shell")
    args = ap.parse_args()

    try:
        bars = load_bars(args.file)
    except Exception as e:
        print(f"ERROR loading bars: {e}", file=sys.stderr)
        return 2

    n = len(bars)
    min_bars = args.length * 2 + 1
    if n < min_bars:
        print(f"ERROR: need at least {min_bars} bars, got {n}", file=sys.stderr)
        return 3

    normalized = [_normalize_bar(b) for b in bars]
    last_close = normalized[-1]["close"]

    try:
        res = compute_adx(normalized, length=args.length)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 3

    last_adx = res["adx"]
    last_plus_di = res["plus_di"]
    last_minus_di = res["minus_di"]

    regime, strat = label_regime(last_adx, last_plus_di, last_minus_di)
    if args.quick:
        print(
            f"ADX={last_adx} +DI={last_plus_di} "
            f"-DI={last_minus_di} REGIME={regime} BARS={n}"
        )
    else:
        print(json.dumps({
            "last_adx": last_adx,
            "last_plus_di": last_plus_di,
            "last_minus_di": last_minus_di,
            "regime": regime,
            "strategy_hint": strat,
            "bars_used": n,
            "length": args.length,
        }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
