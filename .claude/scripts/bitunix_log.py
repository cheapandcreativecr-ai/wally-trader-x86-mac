#!/usr/bin/env python3
"""bitunix_log.py — append signals + outcomes to bitunix log files.

Subcommands:
  append-signal --stdin    : parse a /signal markdown report and append entry to MD + CSV
  append-outcome SYMBOL OUTCOME EXIT_PRICE [--id N] [--pnl USD] : close an open entry

Profile gating: only writes when WALLY_PROFILE == "bitunix". Otherwise no-op exit 0.

wally_core delegation: after writing the local MD+CSV (primary), fan-out to
wally_core.signals.log_signal / close_signal_outcome for Notion/hybrid backend
support.  Fire-and-forget — any wally_core error is logged but never surfaces
to the caller, preserving zero CLI-surface behavior change.
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Auto-inject wally_core from worktree (no venv activation required).
# Falls back gracefully when the shared/ tree is absent (e.g. plain-repo install).
_SHARED = Path(__file__).resolve().parent.parent.parent / "shared/wally_core/src"
if _SHARED.exists() and str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

CR_OFFSET = timezone(timedelta(hours=-6))

ENTRY_HEADER_RE = re.compile(
    r"^## (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}) — (\S+) (LONG|SHORT)",
    re.MULTILINE
)

CSV_FIELDS = [
    "date", "time", "symbol", "side", "entry", "sl", "tp", "leverage_signal",
    "day_of_week", "filters_4", "multifactor", "ml_score", "chainlink_delta",
    "regime", "pillars_4_count", "saturday", "verdict", "decision", "size_pct",
    "executed", "exit_price", "exit_reason", "pnl_usd", "duration_h",
    "hypothetical_outcome", "learning", "tier",
]

# Legacy schemas auto-migrated on detection (header → backfill values).
# Each entry: (old_header_tuple, default_values_for_new_columns_dict).
LEGACY_SCHEMAS: list[tuple[tuple[str, ...], dict[str, str]]] = [
    (
        # Pre-tier-0 schema (added 2026-05-05)
        (
            "date", "time", "symbol", "side", "entry", "sl", "tp", "leverage_signal",
            "day_of_week", "filters_4", "multifactor", "ml_score", "chainlink_delta",
            "regime", "pillars_4_count", "saturday", "verdict", "decision", "size_pct",
            "executed", "exit_price", "exit_reason", "pnl_usd", "duration_h",
            "hypothetical_outcome", "learning",
        ),
        {"tier": "standard"},
    ),
]


def repo_root() -> Path:
    """Find repo root by walking up from cwd looking for .claude/ dir."""
    cur = Path.cwd()
    while cur != cur.parent:
        if (cur / ".claude").is_dir():
            return cur
        cur = cur.parent
    return Path.cwd()


def bitunix_paths() -> tuple[Path, Path]:
    root = repo_root()
    base = root / ".claude" / "profiles" / "bitunix" / "memory"
    return base / "signals_received.md", base / "signals_received.csv"


def is_bitunix_profile() -> bool:
    return os.environ.get("WALLY_PROFILE", "") == "bitunix"


def log_error(msg: str, body: str = "") -> None:
    err_path = repo_root() / ".claude" / "cache" / "bitunix_log_errors.log"
    err_path.parent.mkdir(parents=True, exist_ok=True)
    with err_path.open("a", encoding="utf-8") as f:
        f.write(f"--- {datetime.now(CR_OFFSET).isoformat()} {msg} ---\n")
        if body:
            f.write(body + "\n")


def parse_signal_report(text: str) -> dict[str, str]:
    """Extract fields from a canonical /signal markdown report.

    Raises ValueError on parse failure (missing required fields).
    """

    def grab(pattern: str, default: str = "", flags: int = 0) -> str:
        m = re.search(pattern, text, flags)
        return m.group(1).strip() if m else default

    fields: dict[str, str] = {
        "symbol": grab(r"\*\*Symbol:\*\*\s*(\S+)"),
        "side": grab(r"\*\*Side:\*\*\s*(LONG|SHORT)"),
        "entry": grab(r"\*\*Entry:\*\*\s*([\d.]+)"),
        "sl": grab(r"\*\*SL:\*\*\s*([\d.]+)"),
        "tp": grab(r"\*\*TP:\*\*\s*([\d.]+)"),
        "leverage_signal": grab(r"\*\*Leverage signal:\*\*\s*([\d.]+)x?"),
        "day_of_week": grab(r"\*\*Day-of-week:\*\*\s*(\w+)"),
        "filters_4": grab(r"4 filtros t[eé]cnicos:\*\*\s*(\d)/4"),
        "multifactor": grab(r"Multi-Factor:\*\*\s*([+\-\d]+)"),
        "ml_score": grab(r"\bML:\*\*\s*([\d.]+)"),
        "chainlink_delta": grab(r"Chainlink delta:\*\*\s*([\d.]+)%"),
        "regime": grab(r"R[eé]gimen:\*\*\s*(RANGE|TRENDING|VOLATILE)"),
        "pillars_4_count": grab(r"4-Pilar Neptune SMC:\*\*\s*(\d)/4"),
        "verdict": grab(r"Veredicto:\*\*\s*(APPROVE_FULL|APPROVE_HALF|REJECT)"),
        "decision": grab(r"Decisi[oó]n:\*\*\s*([^\n]+)"),
        "validation_score": grab(r"Validation Score:\*\*\s*(\d+)/100"),
        "tier": grab(r"\*\*Tier:\*\*\s*(\w+)") or "standard",
    }

    # Saturday Protocol: "N" if N/A or absent, "Y" if explicitly active
    sat_line = grab(r"Saturday Protocol:\*\*\s*([^\n]+)")
    fields["saturday"] = "N" if (not sat_line or "N/A" in sat_line) else "Y"

    # size_pct: extract the numeric % from the decision line
    size_m = re.search(r"size\s+(\d+)%", fields["decision"], re.IGNORECASE)
    if not size_m:
        # fallback: look anywhere in document for "full size N%" or "half size N%"
        size_m = re.search(r"(?:full|half)\s+size\s+(\d+)%", text, re.IGNORECASE)
    fields["size_pct"] = size_m.group(1) if size_m else ""

    # executed flag
    decision_lower = fields["decision"].lower()
    if "ejecutado" in decision_lower:
        fields["executed"] = "yes"
    elif "skip" in decision_lower:
        fields["executed"] = "no"
    else:
        fields["executed"] = ""

    # Check required fields
    required = ["symbol", "side", "entry", "sl", "tp", "verdict"]
    missing = [k for k in required if not fields[k]]
    if missing:
        raise ValueError(f"Missing required fields in signal report: {missing}")

    # Timestamp in CR timezone
    now = datetime.now(CR_OFFSET)
    fields["date"] = now.strftime("%Y-%m-%d")
    fields["time"] = now.strftime("%H:%M")

    # Ensure all CSV fields have a value (empty string default)
    for k in ("exit_price", "exit_reason", "pnl_usd", "duration_h",
              "hypothetical_outcome", "learning"):
        fields.setdefault(k, "")

    return fields


def render_md_entry(fields: dict[str, str]) -> str:
    """Render a markdown block for the signals_received.md file."""
    tier = fields.get("tier", "standard") or "standard"
    return (
        f"\n## {fields['date']} {fields['time']} — "
        f"{fields['symbol']} {fields['side']} {fields['leverage_signal']}x\n\n"
        f"**Señal recibida:** entry {fields['entry']}, SL {fields['sl']}, "
        f"TP {fields['tp']}, leverage {fields['leverage_signal']}x\n"
        f"**Source:** punkchainer Discord\n"
        f"**Tier:** {tier}\n"
        f"**Day-of-week:** {fields['day_of_week']}\n\n"
        f"**Pipeline validación (8 steps):**\n"
        f"  1. Parse OK\n"
        f"  2. 4 filtros técnicos: {fields['filters_4']}/4\n"
        f"  3. Multi-Factor: {fields['multifactor']} ({fields['side']}) | ML: {fields['ml_score']}\n"
        f"  4. Chainlink delta: {fields['chainlink_delta']}% (OK)\n"
        f"  5. Régimen: {fields['regime']} — compatible con {fields['side']}? Y\n"
        f"  6. **4-Pilar Neptune SMC: {fields['pillars_4_count']}/4**\n"
        f"  7. Saturday Protocol activo? {fields['saturday']}\n"
        f"  8. Veredicto: {fields['verdict']}\n\n"
        f"**Validation Score:** {fields['validation_score']}/100\n"
        f"**Decisión:** {fields['decision']}\n\n"
        f"**Resultado real:**\n"
        f"  - Outcome: _pendiente_\n"
        f"  - Exit price: _pendiente_\n"
        f"  - PnL: _pendiente_\n"
        f"  - Time to outcome: _pendiente_\n\n"
        f"**Aprendizaje:** _pendiente_\n\n"
        f"---\n"
    )


def append_md(md_path: Path, entry: str) -> None:
    md_path.parent.mkdir(parents=True, exist_ok=True)
    if not md_path.exists():
        md_path.write_text("# Bitunix — Signals received\n\n## Histórico\n\n", encoding="utf-8")
    with md_path.open("a", encoding="utf-8") as f:
        f.write(entry)


def migrate_legacy_csv(csv_path: Path) -> bool:
    """Detect and auto-migrate a legacy CSV schema in-place.

    Returns True if migration was performed, False if file is already current
    (or empty/missing). Raises ValueError if schema is unrecognized.
    """
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return False

    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        try:
            header = tuple(next(reader))
        except StopIteration:
            return False

    if header == tuple(CSV_FIELDS):
        return False  # already current

    # Search for matching legacy schema
    for legacy_header, defaults in LEGACY_SCHEMAS:
        if header == legacy_header:
            # Backfill missing columns and rewrite
            with csv_path.open(newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            for row in rows:
                for k, v in defaults.items():
                    row.setdefault(k, v)
            tmp_path = csv_path.with_suffix(csv_path.suffix + ".migrating")
            with tmp_path.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
                w.writeheader()
                for row in rows:
                    w.writerow({k: row.get(k, "") for k in CSV_FIELDS})
            tmp_path.replace(csv_path)
            return True

    raise ValueError(
        f"CSV schema mismatch in {csv_path.name}. "
        f"Expected: {','.join(CSV_FIELDS)[:80]}... "
        f"Got: {','.join(header)[:80]}..."
    )


def append_csv(csv_path: Path, fields: dict[str, str]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    migrate_legacy_csv(csv_path)
    if csv_path.exists() and csv_path.stat().st_size > 0:
        write_header = False
    else:
        write_header = True
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if write_header:
            w.writeheader()
        w.writerow({k: fields.get(k, "") for k in CSV_FIELDS})


# ---------------------------------------------------------------------------
# wally_core fan-out helpers (fire-and-forget; zero CLI behavior change)
# ---------------------------------------------------------------------------

def _wc_fanout_enabled() -> bool:
    """Return True only when the user has explicitly opted into a wally_core
    backend that does NOT also write to the same signals_received.csv on disk.

    - WALLY_MEMORY_BACKEND=notion  → Notion-only, safe to fan-out
    - WALLY_MEMORY_BACKEND=local   → writes same CSV path, skip
    - WALLY_MEMORY_BACKEND=hybrid  → local layer writes same CSV path, skip
    - unset (default=hybrid)       → same as hybrid, skip
    """
    return os.environ.get("WALLY_MEMORY_BACKEND", "") == "notion"


def _wc_log_signal_fanout(fields: dict[str, str], signal_text: str) -> None:
    """Delegate signal to wally_core.signals.log_signal (secondary persistence).

    Constructs a wally_core.memory.Signal from the parsed fields and calls
    log_signal so that Notion/hybrid backends also receive the entry.

    Only active when WALLY_MEMORY_BACKEND=notion (see _wc_fanout_enabled).
    Any import or runtime error is silently logged — never propagated.
    """
    if not _wc_fanout_enabled():
        return
    try:
        from wally_core.memory.schemas import Signal, Side, SignalDecision
        from wally_core.signals import log_signal

        verdict = fields.get("verdict", "")
        if verdict == "APPROVE_FULL":
            decision = SignalDecision.GO
        elif verdict == "APPROVE_HALF":
            decision = SignalDecision.WARN
        else:
            decision = SignalDecision.NO_GO

        ts_str = f"{fields['date']}T{fields['time']}:00-06:00"
        tp_val = float(fields.get("tp") or 0)
        sig = Signal(
            ts=datetime.fromisoformat(ts_str),
            profile="bitunix",
            source="discord",
            symbol=fields["symbol"],
            side=Side(fields["side"]),
            entry=float(fields["entry"]),
            sl=float(fields["sl"]),
            tp1=tp_val,
            tp2=tp_val,
            tp3=tp_val,
            leverage=int(float(fields.get("leverage_signal") or 1)),
            score=int(fields.get("validation_score") or 0),
            decision=decision,
            raw_message=signal_text,
        )
        log_signal(sig)
    except Exception as e:
        log_error(f"wc_log_signal_fanout failed: {e}")


def _wc_close_signal_fanout(symbol: str, outcome_str: str,
                            exit_price: float, pnl: float | None) -> None:
    """Delegate outcome to wally_core.signals.close_signal_outcome.

    Looks up the most recent open wally_core Signal for the symbol and closes
    it.  Only active when WALLY_MEMORY_BACKEND=notion (see _wc_fanout_enabled).
    Fire-and-forget — errors are logged, never propagated.
    """
    if not _wc_fanout_enabled():
        return
    try:
        from wally_core.memory import get_backend, SignalOutcome

        outcome_map = {
            "TP1": SignalOutcome.TP1,
            "TP2": SignalOutcome.TP2,
            "TP3": SignalOutcome.TP3,
            "SL": SignalOutcome.SL,
            "manual": SignalOutcome.MANUAL,
        }
        wc_outcome = outcome_map.get(outcome_str, SignalOutcome.MANUAL)
        backend = get_backend("bitunix")
        open_sigs = list(backend.read_signals("bitunix", status=SignalOutcome.PENDING))
        # Find the latest pending signal for this symbol
        sym_norm = symbol.replace(".P", "").upper()
        matches = [s for s in open_sigs if s.symbol.replace(".P", "").upper() == sym_norm]
        if not matches:
            return  # nothing to close in wally_core (may not have been logged there)
        latest = matches[-1]
        backend.update_signal_outcome(
            latest.id, wc_outcome, exit_price, pnl if pnl is not None else 0.0
        )
    except Exception as e:
        log_error(f"wc_close_signal_fanout failed: {e}")


def cmd_append_signal(args: argparse.Namespace) -> int:
    if not is_bitunix_profile():
        return 0  # silent no-op

    text = sys.stdin.read()
    try:
        fields = parse_signal_report(text)
    except ValueError as e:
        log_error(f"parse failed: {e}", text)
        print(
            "WARNING: bitunix_log parse failed, see cache/bitunix_log_errors.log",
            file=sys.stderr,
        )
        return 1

    md_path, csv_path = bitunix_paths()
    try:
        append_md(md_path, render_md_entry(fields))
        append_csv(csv_path, fields)
    except (OSError, ValueError) as e:
        log_error(f"write failed: {e}")
        print(
            f"WARNING: bitunix_log write failed ({e}), see cache/bitunix_log_errors.log",
            file=sys.stderr,
        )
        return 1

    # Fan-out to wally_core backend (Notion/hybrid) — fire-and-forget.
    _wc_log_signal_fanout(fields, text)

    print(f"bitunix_log: appended {fields['symbol']} {fields['side']} to {md_path.name}")
    return 0


def _fmt_price(price: float) -> str:
    """Format price as integer string if whole number, else float string."""
    return str(int(price)) if price == int(price) else str(price)


def find_open_entries(md_text: str, symbol: str) -> list[tuple[int, int, str]]:
    """Return list of (start_idx, end_idx, header_line) for open entries of `symbol`.

    An entry is "open" if its `Outcome:` line is `_pendiente_`.
    """
    matches = list(ENTRY_HEADER_RE.finditer(md_text))
    open_entries = []
    for i, m in enumerate(matches):
        if m.group(3) != symbol:
            continue
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md_text)
        block = md_text[start:end]
        if "Outcome: _pendiente_" in block:
            open_entries.append((start, end, m.group(0)))
    return open_entries


def update_md_outcome(md_path: Path, start: int, end: int,
                      outcome: str, exit_price: float, pnl: float | None,
                      duration_h: float, held_pillars: bool) -> None:
    text = md_path.read_text(encoding="utf-8")
    block = text[start:end]
    block = block.replace("Outcome: _pendiente_", f"Outcome: {outcome}")
    block = block.replace("Exit price: _pendiente_", f"Exit price: {_fmt_price(exit_price)}")
    pnl_str = f"{pnl:.2f}" if pnl is not None else "_calc_pendiente_"
    block = block.replace("PnL: _pendiente_", f"PnL: {pnl_str}")
    block = block.replace("Time to outcome: _pendiente_",
                          f"Time to outcome: {duration_h:.1f}h")
    pillars_str = "Y" if held_pillars else "N"
    if "Held 4-pilar al exit?" not in block:
        block = block.replace(
            f"Time to outcome: {duration_h:.1f}h",
            f"Time to outcome: {duration_h:.1f}h\n  - Held 4-pilar al exit? {pillars_str}"
        )
    md_path.write_text(text[:start] + block + text[end:], encoding="utf-8")


def update_csv_outcome(csv_path: Path, row_index: int,
                       outcome: str, exit_price: float, pnl: float | None,
                       duration_h: float) -> None:
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    rows[row_index]["exit_price"] = _fmt_price(exit_price)
    rows[row_index]["exit_reason"] = outcome
    rows[row_index]["pnl_usd"] = f"{pnl:.2f}" if pnl is not None else ""
    rows[row_index]["duration_h"] = f"{duration_h:.1f}"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        w.writerows(rows)


def find_open_csv_row(csv_path: Path, symbol: str) -> int | None:
    """Return index of the most recent open (no exit_price) row for symbol."""
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    for i in range(len(rows) - 1, -1, -1):
        if rows[i]["symbol"] == symbol and not rows[i].get("exit_price"):
            return i
    return None


def compute_duration_hours(date_str: str, time_str: str, now: datetime) -> float:
    entry_dt = datetime.fromisoformat(f"{date_str}T{time_str}:00-06:00")
    return (now - entry_dt).total_seconds() / 3600.0


def cmd_append_outcome(args: argparse.Namespace) -> int:
    if not is_bitunix_profile():
        print("Solo aplica a profile bitunix.")
        return 0
    md_path, csv_path = bitunix_paths()
    if not md_path.exists():
        print(f"No bitunix log found at {md_path}.", file=sys.stderr)
        return 1

    md_text = md_path.read_text(encoding="utf-8")
    open_entries = find_open_entries(md_text, args.symbol)
    if not open_entries:
        print(f"No open signal for {args.symbol}. Nothing to close.", file=sys.stderr)
        return 1
    if len(open_entries) > 1 and args.entry_id is None:
        print(f"Multiple open entries for {args.symbol}:", file=sys.stderr)
        for i, (_, _, header) in enumerate(open_entries):
            print(f"  --id {i}: {header}", file=sys.stderr)
        print("Re-run with --id N", file=sys.stderr)
        return 1
    idx = args.entry_id if args.entry_id is not None else 0
    start, end, header = open_entries[idx]

    m = ENTRY_HEADER_RE.search(md_text[start:end])
    date_str, time_str = m.group(1), m.group(2)
    duration = compute_duration_hours(date_str, time_str, datetime.now(CR_OFFSET))

    held = True  # default optimistic; skip interactive prompt in non-tty (tests/pipes)
    if sys.stdin.isatty():
        # On Windows, isatty() can return True even for piped stdin when the
        # subprocess inherits a console handle. Catching EOFError lets us fall
        # back to the optimistic default whether the prompt path is reached
        # under a real TTY or a misreporting handle.
        try:
            ans = input("Held 4-pilar al exit? [Y/n] ").strip().lower()
            held = ans != "n"
        except EOFError:
            held = True

    try:
        update_md_outcome(md_path, start, end, args.outcome, args.exit_price,
                          args.pnl, duration, held)
        csv_idx = find_open_csv_row(csv_path, args.symbol)
        if csv_idx is not None:
            update_csv_outcome(csv_path, csv_idx, args.outcome, args.exit_price,
                               args.pnl, duration)
    except (OSError, ValueError) as e:
        log_error(f"append-outcome write failed: {e}")
        print(f"ERROR: append-outcome failed ({e})", file=sys.stderr)
        return 1

    # Fan-out to wally_core backend (Notion/hybrid) — fire-and-forget.
    _wc_close_signal_fanout(args.symbol, args.outcome, args.exit_price, args.pnl)

    # Hook for /punk-smart v2 state machine
    try:
        import punk_smart_state as _state
        from datetime import datetime as _dt
        sym_norm = args.symbol.replace(".P", "").upper()
        now = _dt.now(_state.CR_OFFSET)
        if args.outcome == "SL":
            _state.record_sl(sym_norm, now,
                              pnl_usd=(args.pnl if args.pnl is not None else 0.0))
        elif args.outcome.startswith("TP"):
            _state.record_tp(sym_norm, now)
    except Exception as e:
        log_error(f"punk_smart_state hook failed: {e}")

    print(f"bitunix_log: closed {args.symbol} with {args.outcome} at {_fmt_price(args.exit_price)}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description="Bitunix signal log manager",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sig = sub.add_parser("append-signal", help="Append a /signal report to MD + CSV")
    sig.add_argument("--stdin", action="store_true", required=True,
                     help="Read signal report from stdin")
    sig.set_defaults(func=cmd_append_signal)

    out = sub.add_parser("append-outcome", help="Update an open signal with its outcome")
    out.add_argument("symbol")
    out.add_argument("outcome", choices=["TP1", "TP2", "TP3", "SL", "manual"])
    out.add_argument("exit_price", type=float)
    out.add_argument("--id", dest="entry_id", type=int, default=None)
    out.add_argument("--pnl", type=float, default=None)
    out.set_defaults(func=cmd_append_outcome)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
