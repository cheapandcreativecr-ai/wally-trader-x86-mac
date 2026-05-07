"""Unit tests for write/workflow MCP tools (Tasks 6.1–6.6)."""
import pytest
from pathlib import Path

from wally_trader_mcp.tools.signal_validate import signal_validate
from wally_trader_mcp.tools.log_outcome import log_outcome
from wally_trader_mcp.tools.journal_close import journal_close
from wally_trader_mcp.tools.hunt_signals import hunt_signals
from wally_trader_mcp.tools.levels_now import levels_now
from wally_trader_mcp.tools.macross_signal import macross_signal

REPO = Path(__file__).resolve().parent.parent.parent
TRENDING = REPO / "shared/wally_core/tests/fixtures/btc_1h_trending.json"
RANGE = REPO / "shared/wally_core/tests/fixtures/btc_15m_range.json"


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """Use a tmp directory for all memory writes + force local backend."""
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(tmp_path / "profiles"))
    monkeypatch.setenv("WALLY_MEMORY_BACKEND", "local")


# ── signal_validate ───────────────────────────────────────────────────────────

def test_signal_validate_creates_uuid():
    res = signal_validate(
        profile="bitunix", symbol="BTCUSDT", side="LONG",
        entry=68000, sl=67500, tp1=68500, tp2=69000, tp3=70000,
        leverage=10, score=72, decision="GO",
    )
    assert res["uuid"], "uuid should be non-empty"
    assert res["decision"] == "GO"
    assert res["score"] == 72


def test_signal_validate_no_go_decision():
    res = signal_validate(
        profile="bitunix", symbol="ETHUSDT", side="SHORT",
        entry=3000, sl=3050, tp1=2900, tp2=2800, tp3=2700,
        leverage=5, score=38, decision="NO-GO",
        raw_message="low volume, no confluence",
    )
    assert res["decision"] == "NO-GO"
    assert res["uuid"]


def test_signal_validate_non_bitunix_profile_also_works():
    """Other profiles should be allowed to log signals too."""
    res = signal_validate(
        profile="retail", symbol="BTCUSDT", side="LONG",
        entry=68000, sl=67500, tp1=68500, tp2=69000, tp3=70000,
        leverage=10, score=65, decision="GO",
    )
    assert res["uuid"]


# ── log_outcome ───────────────────────────────────────────────────────────────

def test_log_outcome_closes_signal():
    s = signal_validate(
        profile="bitunix", symbol="BTCUSDT", side="LONG",
        entry=68000, sl=67500, tp1=68500, tp2=69000, tp3=70000,
        leverage=10, score=72, decision="GO",
    )
    res = log_outcome(s["uuid"], "TP1", 68500.0, 1.5)
    assert res["status"] == "closed"
    assert res["signal_id"] == s["uuid"]
    assert res["outcome"] == "TP1"


def test_log_outcome_sl_result():
    s = signal_validate(
        profile="bitunix", symbol="SOLUSDT", side="SHORT",
        entry=150, sl=155, tp1=140, tp2=130, tp3=120,
        leverage=10, score=60, decision="GO",
    )
    res = log_outcome(s["uuid"], "SL", 155.0, -2.0)
    assert res["outcome"] == "SL"
    assert res["status"] == "closed"


def test_log_outcome_unknown_id_raises():
    # When profiles dir is empty (no CSV written yet), LocalBackend raises
    # FileNotFoundError (no profiles dir) or KeyError (ID not found after
    # scanning). Both signal "not found" — accept either.
    with pytest.raises((KeyError, FileNotFoundError)):
        log_outcome("nonexistent-uuid-xyz", "TP1", 68000.0, 1.0)


# ── journal_close ─────────────────────────────────────────────────────────────

def test_journal_close_writes_entry():
    res = journal_close(
        profile="bitunix",
        summary="Good day — 1 win, stayed disciplined",
        lessons="Don't chase late entries",
        equity_usd=205.0,
        daily_pnl_usd=5.0,
    )
    assert res["journal_written"] is True
    assert res["equity_appended"] is True
    assert res["profile"] == "bitunix"
    assert res["date"]


def test_journal_close_without_equity():
    res = journal_close(
        profile="retail",
        summary="Flat day",
    )
    assert res["journal_written"] is True
    assert res["equity_appended"] is False
    assert res["metrics"] is None


def test_journal_close_with_trades():
    trades = [
        {"pnl_usd": 5.0, "score": 70},
        {"pnl_usd": -2.0, "score": 40},
        {"pnl_usd": 3.0, "score": 65},
    ]
    res = journal_close(
        profile="bitunix",
        summary="3-trade day",
        trades=trades,
        equity_usd=206.0,
        daily_pnl_usd=6.0,
    )
    assert res["metrics"] is not None
    assert "wr" in res["metrics"]
    assert "sharpe" in res["metrics"]
    assert "n" in res["metrics"]
    assert res["metrics"]["n"] == 3


# ── hunt_signals ──────────────────────────────────────────────────────────────

def test_hunt_signals_rejects_non_bitunix():
    res = hunt_signals("retail", watchlist=[])
    assert "error" in res
    assert res["profile"] == "retail"


def test_hunt_signals_empty_watchlist():
    res = hunt_signals("bitunix", watchlist=[])
    assert res["top"] == []
    assert res["errors"] == []


def test_hunt_signals_returns_top_for_bitunix():
    res = hunt_signals(
        "bitunix",
        watchlist=[
            {"symbol": "BTC", "bars_path": str(TRENDING)},
            {"symbol": "ETH", "bars_path": str(RANGE)},
        ],
        regime="RANGE_CHOP",
    )
    assert "top" in res
    assert len(res["top"]) <= 5
    assert len(res["top"]) == 2
    # Sorted descending by total
    if len(res["top"]) >= 2:
        assert res["top"][0]["total"] >= res["top"][1]["total"]


def test_hunt_signals_error_on_bad_path():
    res = hunt_signals(
        "bitunix",
        watchlist=[{"symbol": "FAKE", "bars_path": "/tmp/nonexistent_xyz.json"}],
    )
    assert len(res["errors"]) == 1
    assert res["errors"][0]["symbol"] == "FAKE"


# ── levels_now ────────────────────────────────────────────────────────────────

def test_levels_now_returns_all_levels():
    res = levels_now(str(TRENDING))
    assert "rsi" in res
    assert "atr" in res
    assert "donchian" in res
    assert "bollinger" in res
    assert "last_close" in res
    assert "high" in res["donchian"] and "low" in res["donchian"]
    assert "upper" in res["bollinger"] and "lower" in res["bollinger"]
    assert 0 <= res["rsi"] <= 100
    assert res["atr"] > 0


def test_levels_now_on_range_bars():
    res = levels_now(str(RANGE))
    assert "rsi" in res
    assert res["donchian"]["high"] >= res["donchian"]["low"]
    assert res["bollinger"]["upper"] >= res["bollinger"]["lower"]


def test_levels_now_insufficient_bars(tmp_path):
    import json
    tiny = [{"open": 100, "high": 101, "low": 99, "close": 100.5, "volume": 500}] * 5
    p = tmp_path / "tiny.json"
    p.write_text(json.dumps(tiny))
    res = levels_now(str(p))
    assert "error" in res


# ── macross_signal ────────────────────────────────────────────────────────────

def test_macross_signal_on_trending_returns_dict():
    res = macross_signal(str(TRENDING))
    assert "signal" in res
    assert res["signal"] in ("LONG", "SHORT", "NONE")
    assert res["ema_fast"] is not None
    assert res["ema_slow"] is not None


def test_macross_signal_on_range_bars():
    res = macross_signal(str(RANGE))
    assert res["signal"] in ("LONG", "SHORT", "NONE")
    assert res["last_close"] > 0


def test_macross_signal_insufficient_bars(tmp_path):
    import json
    tiny = [{"open": 100, "high": 101, "low": 99, "close": 100.5, "volume": 500}] * 5
    p = tmp_path / "tiny.json"
    p.write_text(json.dumps(tiny))
    res = macross_signal(str(p))
    assert res["signal"] == "NONE"
    assert "reason" in res


def test_macross_signal_custom_periods():
    res = macross_signal(str(TRENDING), fast=5, slow=13)
    assert "signal" in res
    assert "ema_fast" in res
