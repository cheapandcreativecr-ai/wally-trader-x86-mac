import csv
import os
import shutil
import subprocess
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "bitunix"
SCRIPT = Path(__file__).parent.parent / "bitunix_log.py"


def run_log(args, cwd, env=None, stdin=None):
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    # Always provide stdin as an empty pipe when not passed — guarantees the
    # subprocess sees a non-TTY stdin on every platform (Windows inherits a
    # console handle by default and sys.stdin.isatty() then returns True,
    # causing interactive input() prompts to fire and EOFError).
    return subprocess.run(
        ["python3", str(SCRIPT), *args],
        capture_output=True, text=True, cwd=cwd, env=full_env,
        input=stdin if stdin is not None else "",
    )


def setup_bitunix_profile(tmp_path: Path) -> Path:
    """Create a minimal bitunix profile structure under tmp_path."""
    p = tmp_path / ".claude" / "profiles" / "bitunix" / "memory"
    p.mkdir(parents=True)
    (p / "signals_received.md").write_text("# Bitunix — Signals received\n\n## Histórico\n\n")
    (p / "signals_received.csv").write_text(
        "date,time,symbol,side,entry,sl,tp,leverage_signal,"
        "day_of_week,filters_4,multifactor,ml_score,chainlink_delta,"
        "regime,pillars_4_count,saturday,verdict,decision,size_pct,"
        "executed,exit_price,exit_reason,pnl_usd,duration_h,"
        "hypothetical_outcome,learning\n"
    )
    return tmp_path


def test_append_signal_no_op_on_non_bitunix_profile(tmp_path):
    setup_bitunix_profile(tmp_path)
    canonical = (FIXTURES / "signal_report_canonical.md").read_text()
    r = run_log(["append-signal", "--stdin"], cwd=tmp_path,
                env={"WALLY_PROFILE": "retail"}, stdin=canonical)
    assert r.returncode == 0
    md = (tmp_path / ".claude/profiles/bitunix/memory/signals_received.md").read_text()
    assert "## 2026" not in md  # no new entry


def test_append_signal_parses_canonical_report(tmp_path):
    setup_bitunix_profile(tmp_path)
    canonical = (FIXTURES / "signal_report_canonical.md").read_text()
    r = run_log(["append-signal", "--stdin"], cwd=tmp_path,
                env={"WALLY_PROFILE": "bitunix"}, stdin=canonical)
    assert r.returncode == 0, r.stderr
    md = (tmp_path / ".claude/profiles/bitunix/memory/signals_received.md").read_text()
    assert "BTCUSDT" in md
    assert "Validation Score:** 78/100" in md
    assert "APPROVE_FULL" in md

    csv_path = tmp_path / ".claude/profiles/bitunix/memory/signals_received.csv"
    rows = list(csv.DictReader(csv_path.open()))
    assert len(rows) == 1
    row = rows[0]
    assert row["symbol"] == "BTCUSDT"
    assert row["side"] == "LONG"
    assert row["entry"] == "67000"
    assert row["sl"] == "66500"
    assert row["tp"] == "68000"
    assert row["leverage_signal"] == "20"
    assert row["day_of_week"] == "Mon"
    assert row["filters_4"] == "4"
    assert row["multifactor"] == "+62"
    assert row["ml_score"] == "71"
    assert row["regime"] == "RANGE"
    assert row["pillars_4_count"] == "4"
    assert row["saturday"] == "N"
    assert row["verdict"] == "APPROVE_FULL"
    assert row["decision"] == "EJECUTADO full size 2%"
    assert row["size_pct"] == "2"
    assert row["executed"] == "yes"


def test_append_signal_malformed_input(tmp_path):
    setup_bitunix_profile(tmp_path)
    r = run_log(["append-signal", "--stdin"], cwd=tmp_path,
                env={"WALLY_PROFILE": "bitunix"},
                stdin="this is not a valid signal report")
    assert r.returncode != 0
    err_log = tmp_path / ".claude/cache/bitunix_log_errors.log"
    assert err_log.exists()
    assert "parse failed" in err_log.read_text().lower()
    md = (tmp_path / ".claude/profiles/bitunix/memory/signals_received.md").read_text()
    assert "## 2026" not in md


def test_append_csv_rejects_schema_mismatch(tmp_path):
    """An existing CSV with different headers must be rejected, not corrupted."""
    setup_bitunix_profile(tmp_path)
    csv_path = tmp_path / ".claude/profiles/bitunix/memory/signals_received.csv"
    # Overwrite with a stale-schema CSV
    csv_path.write_text("date,symbol,side\n2026-05-01,ETHUSDT,LONG\n")
    canonical = (FIXTURES / "signal_report_canonical.md").read_text()
    r = run_log(["append-signal", "--stdin"], cwd=tmp_path,
                env={"WALLY_PROFILE": "bitunix"}, stdin=canonical)
    assert r.returncode != 0
    err_log = tmp_path / ".claude/cache/bitunix_log_errors.log"
    assert err_log.exists()
    log_text = err_log.read_text().lower()
    assert "schema mismatch" in log_text or "write failed" in log_text


def test_append_signal_handles_write_failure(tmp_path):
    """If the MD or CSV write fails (e.g. read-only dir), error is logged not silenced."""
    setup_bitunix_profile(tmp_path)
    base = tmp_path / ".claude/profiles/bitunix/memory"
    # Make the directory read-only
    base.chmod(0o555)
    canonical = (FIXTURES / "signal_report_canonical.md").read_text()
    try:
        r = run_log(["append-signal", "--stdin"], cwd=tmp_path,
                    env={"WALLY_PROFILE": "bitunix"}, stdin=canonical)
    finally:
        # Restore permissions for cleanup
        base.chmod(0o755)
    # Either the script wrote and succeeded (if running as root in CI), or it logged.
    # On macOS/Linux non-root, dir is read-only and write fails → exit 1, error logged.
    if r.returncode != 0:
        err_log = tmp_path / ".claude/cache/bitunix_log_errors.log"
        assert err_log.exists()
        assert "write failed" in err_log.read_text().lower() or "permission" in err_log.read_text().lower()


def setup_with_open_signal(tmp_path: Path) -> Path:
    setup_bitunix_profile(tmp_path)
    base = tmp_path / ".claude/profiles/bitunix/memory"
    shutil.copy(FIXTURES / "signals_received_with_open.md", base / "signals_received.md")
    shutil.copy(FIXTURES / "signals_received_with_open.csv", base / "signals_received.csv")
    return tmp_path


def test_append_outcome_closes_open_entry(tmp_path):
    setup_with_open_signal(tmp_path)
    r = run_log(["append-outcome", "BTCUSDT", "TP1", "68000", "--pnl", "1.50"],
                cwd=tmp_path, env={"WALLY_PROFILE": "bitunix"})
    assert r.returncode == 0, r.stderr
    md = (tmp_path / ".claude/profiles/bitunix/memory/signals_received.md").read_text()
    assert "Outcome: TP1" in md
    assert "Exit price: 68000" in md
    assert "PnL: 1.50" in md
    rows = list(csv.DictReader(
        (tmp_path / ".claude/profiles/bitunix/memory/signals_received.csv").open()))
    assert rows[0]["exit_price"] == "68000"
    assert rows[0]["exit_reason"] == "TP1"
    assert rows[0]["pnl_usd"] == "1.50"


def test_append_outcome_no_open_entry(tmp_path):
    setup_bitunix_profile(tmp_path)  # no open entries
    r = run_log(["append-outcome", "BTCUSDT", "TP1", "68000"],
                cwd=tmp_path, env={"WALLY_PROFILE": "bitunix"})
    assert r.returncode == 1
    assert "no open signal" in r.stderr.lower()


def test_append_outcome_non_bitunix_profile_message(tmp_path):
    setup_bitunix_profile(tmp_path)
    r = run_log(["append-outcome", "BTCUSDT", "TP1", "68000"],
                cwd=tmp_path, env={"WALLY_PROFILE": "retail"})
    assert r.returncode == 0
    assert "bitunix" in r.stdout.lower() or "bitunix" in r.stderr.lower()
