import sys
import json
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / ".claude/scripts"))

from habit_tracker import check_in, compute_streak


def test_check_in_creates_log(tmp_path, monkeypatch):
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(tmp_path / "profiles"))
    answers = {"morning_protocol": True, "checklist": True}
    entry = check_in("bitunix", answers)
    assert entry["score_pct"] == 100
    log = tmp_path / "profiles" / "bitunix" / "memory" / "habits.jsonl"
    assert log.exists()


def test_streak_zero_no_log(tmp_path, monkeypatch):
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(tmp_path / "profiles"))
    res = compute_streak("bitunix")
    assert res["streak"] == 0
    assert res["total_days"] == 0


def test_streak_perfect_days(tmp_path, monkeypatch):
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(tmp_path / "profiles"))
    log = tmp_path / "profiles" / "bitunix" / "memory" / "habits.jsonl"
    log.parent.mkdir(parents=True)

    # Yesterday + today both perfect
    entries = [
        {"date": "2026-05-07", "score_pct": 100},
        {"date": "2026-05-08", "score_pct": 100},
    ]
    with open(log, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")

    res = compute_streak("bitunix")
    assert res["perfect_days"] == 2


def test_streak_broken_by_imperfect(tmp_path, monkeypatch):
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(tmp_path / "profiles"))
    log = tmp_path / "profiles" / "bitunix" / "memory" / "habits.jsonl"
    log.parent.mkdir(parents=True)
    entries = [
        {"date": "2026-05-06", "score_pct": 100},
        {"date": "2026-05-07", "score_pct": 80},  # imperfect
        {"date": "2026-05-08", "score_pct": 100},
    ]
    with open(log, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")

    res = compute_streak("bitunix")
    # Streak broken at imperfect day
    assert res["streak"] <= 1


def test_check_in_score_partial(tmp_path, monkeypatch):
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(tmp_path / "profiles"))
    answers = {"morning_protocol": True, "checklist": False}
    entry = check_in("bitunix", answers)
    assert entry["score_pct"] == 50


def test_check_in_appends_multiple(tmp_path, monkeypatch):
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(tmp_path / "profiles"))
    answers = {"morning_protocol": True}
    check_in("bitunix", answers, today=date(2026, 5, 6))
    check_in("bitunix", answers, today=date(2026, 5, 7))
    log = tmp_path / "profiles" / "bitunix" / "memory" / "habits.jsonl"
    lines = [l for l in log.read_text().splitlines() if l.strip()]
    assert len(lines) == 2


def test_compute_streak_returns_total_days(tmp_path, monkeypatch):
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(tmp_path / "profiles"))
    log = tmp_path / "profiles" / "bitunix" / "memory" / "habits.jsonl"
    log.parent.mkdir(parents=True)
    entries = [
        {"date": "2026-05-06", "score_pct": 100},
        {"date": "2026-05-07", "score_pct": 80},
        {"date": "2026-05-08", "score_pct": 100},
    ]
    with open(log, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
    res = compute_streak("bitunix")
    assert res["total_days"] == 3
