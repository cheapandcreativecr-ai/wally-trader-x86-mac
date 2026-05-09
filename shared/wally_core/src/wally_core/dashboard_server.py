"""Wally Trader Dashboard — FastAPI bind 127.0.0.1:8080.

Provides JSON endpoints + serves single-page HTML dashboard.
Loopback-only by default (no auth needed, never expose to network).
Mobile /api/v1/mobile/* endpoints require X-Api-Key header.
"""
from __future__ import annotations
import csv
import json
import os
import secrets
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles


app = FastAPI(title="Wally Trader Dashboard", version="0.1.0")


# Mobile auth helpers ----------------------------------------

def _mobile_token_path() -> Path:
    return Path.home() / ".wally" / "mobile_token"


def _ensure_mobile_token() -> str:
    """Read or generate mobile API key."""
    p = _mobile_token_path()
    if p.exists():
        return p.read_text().strip()
    p.parent.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(32)
    p.write_text(token)
    p.chmod(0o600)
    return token


@app.middleware("http")
async def mobile_auth_middleware(request: Request, call_next):
    """Require X-Api-Key header on /api/v1/mobile/* endpoints."""
    if request.url.path.startswith("/api/v1/mobile/"):
        provided = request.headers.get("X-Api-Key", "")
        expected = _ensure_mobile_token()
        if provided != expected:
            return JSONResponse(status_code=401, content={"error": "invalid_api_key"})
    return await call_next(request)


# Helpers ----------------------------------------------------

def _profiles_dir() -> Path:
    return Path(os.environ.get("WALLY_PROFILES_DIR", ".claude/profiles"))


def _list_profiles() -> list[str]:
    d = _profiles_dir()
    if not d.exists():
        return []
    return sorted([p.name for p in d.iterdir() if p.is_dir() and not p.name.startswith(".")])


def _read_signals_csv(profile: str, since_days: int = 30) -> list[dict]:
    csv_path = _profiles_dir() / profile / "memory" / "signals_received.csv"
    if not csv_path.exists():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
    out = []
    try:
        with open(csv_path) as f:
            for row in csv.DictReader(f):
                ts_str = row.get("ts") or row.get("timestamp") or row.get("date") or ""
                try:
                    if "T" in ts_str:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    else:
                        ts = datetime.fromisoformat(ts_str + "T00:00:00+00:00")
                except Exception:
                    continue
                if ts < cutoff:
                    continue
                row["_ts_iso"] = ts.isoformat()
                out.append(row)
    except Exception:
        pass
    return out


# Endpoints --------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def root():
    """Serve dashboard HTML."""
    here = Path(__file__).parent
    index = here / "dashboard" / "index.html"
    if index.exists():
        return HTMLResponse(content=index.read_text())
    return HTMLResponse(content="<h1>Dashboard files missing</h1>", status_code=500)


@app.get("/api/health")
def api_health():
    return {"status": "ok", "version": "0.1.0", "ts": datetime.now(timezone.utc).isoformat()}


@app.get("/api/profiles")
def api_profiles():
    """List all available profiles + basic state."""
    profiles = []
    for name in _list_profiles():
        signals = _read_signals_csv(name, since_days=1)
        pending = [s for s in signals if not s.get("outcome") or s.get("outcome") == "pending"]
        profiles.append({
            "name": name,
            "open_count": len(pending),
            "today_count": len(signals),
        })
    return {"profiles": profiles}


@app.get("/api/profile/{profile}/state")
def api_profile_state(profile: str):
    """Profile detail: open positions, recent signals, summary."""
    if profile not in _list_profiles():
        raise HTTPException(404, f"Profile {profile} not found")

    signals = _read_signals_csv(profile, since_days=7)
    pending = [s for s in signals if not s.get("outcome") or s.get("outcome") == "pending"]
    closed = [s for s in signals if s.get("outcome") and s.get("outcome") != "pending"]

    # Compute today P&L
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_pnl = 0.0
    for s in closed:
        if today_str in (s.get("ts") or s.get("timestamp") or s.get("date") or ""):
            try:
                today_pnl += float(s.get("pnl_usd") or 0)
            except ValueError:
                pass

    return {
        "profile": profile,
        "open_positions": pending[:20],
        "recent_signals": signals[-10:],
        "today_pnl_usd": round(today_pnl, 2),
        "n_open": len(pending),
        "n_closed_7d": len(closed),
    }


@app.get("/api/portfolio/heat")
def api_portfolio_heat():
    """Aggregate portfolio heat across all profiles with open positions."""
    from .portfolio import compute_heat, Position

    all_positions = []
    capital_total = 0.0
    by_profile = {}

    for profile in _list_profiles():
        signals = _read_signals_csv(profile, since_days=2)
        pending = [s for s in signals if not s.get("outcome") or s.get("outcome") == "pending"]
        positions_this = []
        for s in pending:
            try:
                qty = 0.0  # not always logged; default 0 — heat will be 0 for these
                pos = Position(
                    symbol=s.get("symbol", "?"),
                    side=s.get("side", "?"),
                    margin_usd=0.0,
                    leverage=int(s.get("leverage_signal") or s.get("leverage") or 10),
                    entry_price=float(s.get("entry") or 0),
                    sl_price=float(s.get("sl")) if s.get("sl") else None,
                    qty=qty,
                )
                positions_this.append(pos)
            except (ValueError, TypeError):
                continue
        all_positions.extend(positions_this)
        by_profile[profile] = len(positions_this)
        # naive capital estimate
        capital_total += 100.0  # placeholder: read from profile config in production

    if capital_total == 0:
        capital_total = 1000.0  # safe default

    report = compute_heat(all_positions, capital_total)
    return {
        "total_heat_pct": report.total_heat_pct,
        "n_positions": report.n_positions,
        "breach": report.breach,
        "breakdown": report.breakdown,
        "capital_estimate": capital_total,
        "by_profile": by_profile,
    }


@app.get("/api/discipline/tilt/{profile}")
def api_discipline_tilt(profile: str):
    """Tilt score for a profile."""
    from .discipline import tilt_score, TradeRecord, cooldown_active

    if profile not in _list_profiles():
        raise HTTPException(404, f"Profile {profile} not found")

    signals = _read_signals_csv(profile, since_days=1)
    trades = []
    for s in signals:
        try:
            ts = datetime.fromisoformat(s["_ts_iso"])
            pnl = float(s.get("pnl_usd") or 0)
            outcome = (s.get("outcome") or "").upper()
            trades.append(TradeRecord(
                timestamp=ts,
                symbol=s.get("symbol", "?"),
                side=s.get("side", "?"),
                pnl_usd=pnl,
                margin_usd=0.0,
                is_loss=outcome == "SL" or pnl < 0,
            ))
        except Exception:
            continue

    report = tilt_score(recent_trades=trades)
    cs = cooldown_active(profile=profile, cooldown_file=".claude/cache/cooldowns.json")

    return {
        "profile": profile,
        "score": report.score,
        "level": report.level.value,
        "flags": report.flags,
        "cooldown_active": cs.active,
        "cooldown_minutes_remaining": cs.minutes_remaining,
    }


@app.get("/api/calibration/divergence/{profile}")
def api_calibration_divergence(profile: str, window_days: int = 30):
    """Live vs backtest divergence."""
    from .calibration import compare_live_vs_backtest

    if profile not in _list_profiles():
        raise HTTPException(404, f"Profile {profile} not found")

    profiles_dir = _profiles_dir()
    backtest_path = profiles_dir / profile / "memory" / "backtest_baseline.csv"

    live_signals = _read_signals_csv(profile, since_days=window_days)
    live_trades = [{"pnl_usd": float(s.get("pnl_usd") or 0)} for s in live_signals if s.get("pnl_usd")]

    if not backtest_path.exists():
        return {
            "profile": profile,
            "window_days": window_days,
            "info": "no_backtest_baseline",
            "live_n": len(live_trades),
        }

    backtest_trades = []
    with open(backtest_path) as f:
        for row in csv.DictReader(f):
            try:
                backtest_trades.append({"pnl_usd": float(row.get("pnl_usd") or 0)})
            except ValueError:
                continue

    if not backtest_trades or not live_trades:
        return {
            "profile": profile,
            "window_days": window_days,
            "info": "insufficient_data",
            "live_n": len(live_trades),
            "backtest_n": len(backtest_trades),
        }

    report = compare_live_vs_backtest(live_trades, backtest_trades)
    return {
        "profile": profile,
        "window_days": window_days,
        "live": report.live.__dict__,
        "backtest": report.backtest.__dict__,
        "wr_drift_pct": report.wr_drift_pct,
        "pf_drift_pct": report.pf_drift_pct,
        "sharpe_drift": report.sharpe_drift,
        "severity": report.severity,
        "flags": report.flags,
    }


@app.get("/api/positions")
def api_positions_all():
    """All open positions across profiles."""
    rows = []
    for profile in _list_profiles():
        signals = _read_signals_csv(profile, since_days=2)
        for s in signals:
            outcome = s.get("outcome") or "pending"
            if outcome and outcome != "pending":
                continue
            rows.append({
                "profile": profile,
                "symbol": s.get("symbol", "?"),
                "side": s.get("side", "?"),
                "entry": s.get("entry"),
                "sl": s.get("sl"),
                "tp": s.get("tp"),
                "leverage": s.get("leverage_signal") or s.get("leverage"),
                "ts": s.get("_ts_iso"),
            })
    return {"positions": rows, "count": len(rows)}


# Mobile endpoints -------------------------------------------

@app.get("/api/v1/mobile/dashboard")
def api_mobile_dashboard():
    """Aggregated mobile-friendly dashboard view."""
    profiles = []
    for name in _list_profiles():
        signals = _read_signals_csv(name, since_days=1)
        pending = [s for s in signals if not s.get("outcome") or s.get("outcome") == "pending"]
        profiles.append({"name": name, "open": len(pending), "today_signals": len(signals)})

    return {
        "profiles": profiles,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/mobile/positions")
def api_mobile_positions():
    """Mobile-friendly positions view."""
    return api_positions_all()


# PWA static files -------------------------------------------

@app.get("/manifest.json")
def manifest():
    here = Path(__file__).parent
    p = here / "dashboard" / "manifest.json"
    if p.exists():
        return FileResponse(p, media_type="application/manifest+json")
    raise HTTPException(404)


@app.get("/sw.js")
def service_worker():
    here = Path(__file__).parent
    p = here / "dashboard" / "sw.js"
    if p.exists():
        return FileResponse(p, media_type="application/javascript")
    raise HTTPException(404)


# Serve dashboard static --------------------------------------

_HERE = Path(__file__).parent
_DASHBOARD_DIR = _HERE / "dashboard"

if _DASHBOARD_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_DASHBOARD_DIR)), name="static")


def main():
    """Entry point: uvicorn run on 127.0.0.1:8080."""
    import uvicorn
    uvicorn.run(
        "wally_core.dashboard_server:app",
        host="127.0.0.1",
        port=8080,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
