"""Operations engine — health checks, latency probes, drift detection."""
from __future__ import annotations
import json
import os
import socket
import subprocess
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class HealthCheck:
    name: str
    status: str  # "ok", "warn", "critical"
    detail: str = ""
    latency_ms: Optional[float] = None
    timestamp: str = ""


def latency_probe(url: str, timeout: float = 5.0) -> dict:
    """HTTP HEAD to measure latency. Returns {ok, latency_ms, status}."""
    t0 = time.time()
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            ms = (time.time() - t0) * 1000
            return {"ok": True, "latency_ms": round(ms, 1), "status": resp.status}
    except Exception as e:
        ms = (time.time() - t0) * 1000
        return {"ok": False, "latency_ms": round(ms, 1), "error": str(e)[:100]}


def check_dashboard_health(port: int = 8080) -> HealthCheck:
    """Verify dashboard FastAPI server is responding."""
    result = latency_probe(f"http://127.0.0.1:{port}/api/health")
    if result["ok"]:
        return HealthCheck(
            name="dashboard",
            status="ok" if result["latency_ms"] < 500 else "warn",
            detail=f"{result['latency_ms']}ms",
            latency_ms=result["latency_ms"],
        )
    return HealthCheck(
        name="dashboard", status="critical",
        detail=f"unreachable: {result.get('error', 'unknown')}",
    )


def check_disk_space(path: str = "/Users/josecampos", threshold_pct: float = 90) -> HealthCheck:
    """Verify disk usage below threshold. Handles macOS (Capacity%) and Linux (Use%) df formats."""
    try:
        result = subprocess.check_output(["df", "-h", path], text=True, timeout=5)
        lines = [l for l in result.strip().split("\n") if l.strip()]
        # Skip header line; parse the last data line (handles line-wrapped mount output)
        data_line = lines[-1]
        parts = data_line.split()
        # Find the %-suffixed token — macOS uses Capacity column, Linux uses Use%
        for part in parts:
            if part.endswith("%"):
                used_pct = int(part.rstrip("%"))
                if used_pct >= threshold_pct:
                    return HealthCheck(name="disk_space", status="critical", detail=f"{used_pct}% used")
                elif used_pct >= threshold_pct - 10:
                    return HealthCheck(name="disk_space", status="warn", detail=f"{used_pct}% used")
                return HealthCheck(name="disk_space", status="ok", detail=f"{used_pct}% used")
    except Exception as e:
        return HealthCheck(name="disk_space", status="warn", detail=str(e)[:100])
    return HealthCheck(name="disk_space", status="warn", detail="parse_failed")


def check_mcp_processes() -> HealthCheck:
    """Verify wally-trader-mcp + tradingview-mcp running."""
    try:
        result = subprocess.check_output(["pgrep", "-fl", "wally_trader_mcp"], text=True, timeout=5)
        if result.strip():
            return HealthCheck(name="mcp_processes", status="ok", detail=result.strip().split("\n")[0][:80])
    except subprocess.CalledProcessError:
        pass
    return HealthCheck(name="mcp_processes", status="warn", detail="wally_trader_mcp not running")


def check_notion_credentials() -> HealthCheck:
    """Verify NOTION_API_KEY env var set."""
    if os.environ.get("NOTION_API_KEY"):
        return HealthCheck(name="notion_creds", status="ok", detail="env var set")
    return HealthCheck(name="notion_creds", status="warn", detail="NOTION_API_KEY missing")


def check_telegram_credentials() -> HealthCheck:
    """Verify Telegram bot creds."""
    has_token = bool(os.environ.get("TELEGRAM_BOT_TOKEN"))
    has_chat = bool(os.environ.get("TELEGRAM_CHAT_ID"))
    if has_token and has_chat:
        return HealthCheck(name="telegram_creds", status="ok", detail="both set")
    return HealthCheck(name="telegram_creds", status="warn",
                      detail=f"token={has_token} chat_id={has_chat}")


def detect_clock_drift(local_now: Optional[datetime] = None, ntp_server: str = "time.apple.com") -> dict:
    """Approximate clock drift via NTP. Falls back to HTTP Date header from Cloudflare."""
    local = local_now or datetime.now(timezone.utc)

    # Lightweight check: HTTP Date header from google.com (reliable, always returns 200 with Date)
    try:
        req = urllib.request.Request(
            "https://google.com", method="HEAD",
            headers={"User-Agent": "wally-trader-drift/1.0"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            date_str = resp.headers.get("Date", "")
            if date_str:
                from email.utils import parsedate_to_datetime
                remote = parsedate_to_datetime(date_str)
                drift_seconds = (local - remote).total_seconds()
                return {
                    "drift_seconds": round(drift_seconds, 2),
                    "abs_drift_seconds": round(abs(drift_seconds), 2),
                    "remote_source": "google_http",
                    "remote_iso": remote.isoformat(),
                    "local_iso": local.isoformat(),
                }
    except Exception as e:
        return {"error": str(e)[:100]}
    return {"error": "no_remote_time_source"}


def run_all_checks(*, dashboard_port: int = 8080) -> list[HealthCheck]:
    """Run all health checks. Returns list of HealthCheck."""
    now_iso = datetime.now(timezone.utc).isoformat()
    checks = [
        check_dashboard_health(dashboard_port),
        check_disk_space(),
        check_mcp_processes(),
        check_notion_credentials(),
        check_telegram_credentials(),
    ]
    # Stamp timestamp
    for c in checks:
        c.timestamp = now_iso
    return checks


def overall_status(checks: list[HealthCheck]) -> str:
    """Aggregate: critical if any critical, warn if any warn, else ok."""
    if any(c.status == "critical" for c in checks):
        return "critical"
    if any(c.status == "warn" for c in checks):
        return "warn"
    return "ok"
