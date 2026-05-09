import sys
import csv
import subprocess
from pathlib import Path


def test_tax_tracker_runs(tmp_path, monkeypatch):
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(tmp_path / "profiles"))
    csv_path = tmp_path / "profiles" / "bitunix" / "memory" / "signals_received.csv"
    csv_path.parent.mkdir(parents=True)
    with open(csv_path, "w") as f:
        f.write("ts,symbol,side,entry,exit_price,pnl_usd,outcome\n")
        f.write("2026-05-08T12:00:00Z,BTC,LONG,100000,105000,5.0,TP1\n")
        f.write("2026-05-08T13:00:00Z,ETH,SHORT,3000,2900,-3.0,SL\n")

    script = Path(__file__).resolve().parent.parent.parent.parent / ".claude/scripts/tax_tracker.py"
    result = subprocess.run(
        [sys.executable, str(script), "--profile", "bitunix", "--year", "2026"],
        capture_output=True, text=True,
        env={**__import__("os").environ, "WALLY_PROFILES_DIR": str(tmp_path / "profiles")},
    )
    assert result.returncode == 0

    out_csv = tmp_path / "profiles" / "bitunix" / "memory" / "tax_2026.csv"
    assert out_csv.exists()
    text = out_csv.read_text()
    assert "BTC" in text
    assert "ETH" in text


def test_tax_tracker_skips_pending(tmp_path, monkeypatch):
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(tmp_path / "profiles"))
    csv_path = tmp_path / "profiles" / "bitunix" / "memory" / "signals_received.csv"
    csv_path.parent.mkdir(parents=True)
    with open(csv_path, "w") as f:
        f.write("ts,symbol,side,entry,exit_price,pnl_usd,outcome\n")
        f.write("2026-05-08T12:00:00Z,BTC,LONG,100000,,0,PENDING\n")

    script = Path(__file__).resolve().parent.parent.parent.parent / ".claude/scripts/tax_tracker.py"
    result = subprocess.run(
        [sys.executable, str(script), "--profile", "bitunix", "--year", "2026"],
        capture_output=True, text=True,
        env={**__import__("os").environ, "WALLY_PROFILES_DIR": str(tmp_path / "profiles")},
    )
    # No realized trades exits 0 with info message
    assert result.returncode == 0
    assert "No realized" in result.stdout


def test_tax_tracker_summary_pnl(tmp_path, monkeypatch):
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(tmp_path / "profiles"))
    csv_path = tmp_path / "profiles" / "bitunix" / "memory" / "signals_received.csv"
    csv_path.parent.mkdir(parents=True)
    with open(csv_path, "w") as f:
        f.write("ts,symbol,side,entry,exit_price,pnl_usd,outcome\n")
        f.write("2026-05-08T12:00:00Z,BTC,LONG,100000,105000,10.0,TP1\n")
        f.write("2026-05-08T13:00:00Z,ETH,SHORT,3000,2900,-4.0,SL\n")

    script = Path(__file__).resolve().parent.parent.parent.parent / ".claude/scripts/tax_tracker.py"
    result = subprocess.run(
        [sys.executable, str(script), "--profile", "bitunix", "--year", "2026"],
        capture_output=True, text=True,
        env={**__import__("os").environ, "WALLY_PROFILES_DIR": str(tmp_path / "profiles")},
    )
    assert result.returncode == 0
    assert "+6.00" in result.stdout

    out_csv = tmp_path / "profiles" / "bitunix" / "memory" / "tax_2026.csv"
    text = out_csv.read_text()
    assert "SUMMARY" in text
    assert "+6.00" in text
