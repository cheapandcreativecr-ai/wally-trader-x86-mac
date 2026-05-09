#!/usr/bin/env python3
"""macro_calendar.py — fetch macro events into the cache.

Tries TradingEconomics first, falls back to Forex Factory HTML scraping.
Writes atomically to .claude/cache/macro_events.json.

Usage:
    python3 macro_calendar.py [--cache PATH]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup
from zoneinfo import ZoneInfo

DEFAULT_CACHE = Path(__file__).parent.parent / "cache" / "macro_events.json"
ERROR_LOG = Path(__file__).parent.parent / "cache" / "macro_calendar_errors.log"
TE_URL = "https://api.tradingeconomics.com/calendar"
TE_PARAMS = {
    "c": "guest:guest",
    "country": "united states,euro area,united kingdom,japan",
    "importance": "3",  # high only
    "format": "json",
}
TIMEOUT_SECONDS = 10
CR_OFFSET = timezone(timedelta(hours=-6))
ET = ZoneInfo("America/New_York")
FF_URL = "https://www.forexfactory.com/calendar"
FF_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

# Whitelist patterns (case-insensitive substring match)
WHITELIST = [
    "fomc", "fed interest rate", "fed funds", "powell",
    "inflation rate", "cpi", "core cpi",
    "non farm payrolls", "non-farm payrolls", "nfp",
    "employment change",          # NEW: FF naming for NFP
    "unemployment rate",          # NEW: co-released with NFP
    "average hourly earnings",    # NEW: co-released with NFP
    "pce price index", "core pce",
    "ppi", "producer price",
    "gdp",
    "retail sales",
    "ecb interest rate", "ecb main refinancing", "lagarde",
    "boe interest rate", "bank of england",
    "boj interest rate", "bank of japan",
]


class FetcherError(Exception):
    """Raised when a fetcher cannot produce a usable response."""


def matches_whitelist(name: str) -> bool:
    n = name.lower()
    return any(p in n for p in WHITELIST)


def parse_te_response(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert TradingEconomics calendar response to internal schema."""
    events = []
    for row in raw:
        name = row.get("Event", "").strip()
        if not matches_whitelist(name):
            continue
        # TE Date is naive UTC ISO; convert to CR
        # rstrip("Z") handles Python 3.9 where fromisoformat() doesn't accept Z suffix
        date_str = row["Date"].rstrip("Z")
        utc = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
        cr = utc.astimezone(CR_OFFSET)
        events.append({
            "date": cr.strftime("%Y-%m-%d"),
            "time_cr": cr.strftime("%H:%M"),
            "country": row.get("Country", "").strip(),
            "name": name,
            "impact": "high",  # importance=3 in our query → high
        })
    return events


def fetch_te() -> list[dict[str, Any]]:
    """Fetch from TradingEconomics, return parsed events. Raise FetcherError on failure."""
    try:
        resp = httpx.get(TE_URL, params=TE_PARAMS, timeout=TIMEOUT_SECONDS)
        resp.raise_for_status()
        return parse_te_response(resp.json())
    except (httpx.HTTPError, json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
        raise FetcherError(f"TE fetch failed: {e}") from e


def _parse_ff_date(s: str) -> str:
    """FF dates look like 'MonMay4' or 'Mon May 4'. Normalize to YYYY-MM-DD.

    For year-boundary correctness, picks current year or next year — whichever
    produces a date within ~14 days of now.
    """
    s = s.replace("\n", " ").strip()
    today = datetime.now(CR_OFFSET).date()
    candidates: list[date] = []
    for fmt in ("%Y %a %b %d", "%Y %a%b%d", "%Y %b %d"):
        for year in (today.year, today.year + 1, today.year - 1):
            try:
                dt = datetime.strptime(f"{year} {s}", fmt).date()
                candidates.append(dt)
            except ValueError:
                continue
    if not candidates:
        raise ValueError(f"unparseable FF date: {s!r}")
    # Prefer dates near today (FF shows current week + a bit ahead)
    candidates.sort(key=lambda d: abs((d - today).days))
    return candidates[0].strftime("%Y-%m-%d")


def _convert_ff_time_to_cr(time_text: str, date_iso: str | None = None) -> str | None:
    """FF time like '8:30am' (ET, DST-aware). Convert to CR HH:MM. Return None if unparseable."""
    if not time_text or time_text.lower() in ("all day", "tentative", ""):
        return None
    try:
        time_only = datetime.strptime(time_text.lower(), "%I:%M%p").time()
    except ValueError:
        return None
    # Without a date, fall back to today (best-effort, may be 1h off near DST transitions)
    if date_iso:
        try:
            d = datetime.strptime(date_iso, "%Y-%m-%d").date()
        except ValueError:
            d = datetime.now(CR_OFFSET).date()
    else:
        d = datetime.now(CR_OFFSET).date()
    et_dt = datetime.combine(d, time_only).replace(tzinfo=ET)
    cr_dt = et_dt.astimezone(CR_OFFSET)
    return cr_dt.strftime("%H:%M")


def _ff_currency_to_country(curr: str) -> str:
    return {
        "USD": "United States",
        "EUR": "Euro Area",
        "GBP": "United Kingdom",
        "JPY": "Japan",
    }.get(curr.upper(), curr)


def parse_ff_response(html: str) -> list[dict[str, Any]]:
    """Parse Forex Factory calendar HTML.

    Selectors are based on FF DOM captured 2026-05-04. Key findings vs spec:
    - High impact marker is ``icon--ff-impact-red`` CSS class (no title attribute in live DOM)
    - Date cell text is compact like 'FriMay 8' (no spaces between day-of-week and month)
    - Rows without a .calendar__date cell inherit the date from the prior dated row
    """
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("tr.calendar__row")
    events: list[dict[str, Any]] = []
    current_date_iso: str | None = None

    for row in rows:
        # Update current date if this row carries a date cell
        date_cell = row.select_one(".calendar__date")
        if date_cell:
            text = date_cell.get_text(strip=True)
            if text:
                try:
                    current_date_iso = _parse_ff_date(text)
                except ValueError:
                    pass

        impact_cell = row.select_one(".calendar__impact")
        if not impact_cell:
            continue

        # Real FF DOM uses icon--ff-impact-red class; spec fallback selectors kept as extras
        impact_marker = (
            impact_cell.select_one(".icon--ff-impact-red")
            or impact_cell.select_one("[title*='High Impact']")
            or impact_cell.select_one(".impact--high")
        )
        if not impact_marker:
            continue

        time_cell = row.select_one(".calendar__time")
        time_text = time_cell.get_text(strip=True) if time_cell else ""
        currency_cell = row.select_one(".calendar__currency")
        currency = currency_cell.get_text(strip=True) if currency_cell else ""

        event_name_cell = (
            row.select_one(".calendar__event-title")
            or row.select_one(".calendar__event")
        )
        if not event_name_cell:
            continue
        name = event_name_cell.get_text(strip=True)

        if not matches_whitelist(name):
            continue
        if not current_date_iso:
            continue

        time_cr = _convert_ff_time_to_cr(time_text, current_date_iso)
        if not time_cr:
            continue

        events.append({
            "date": current_date_iso,
            "time_cr": time_cr,
            "country": _ff_currency_to_country(currency),
            "name": name,
            "impact": "high",
        })
    return events


def fetch_ff() -> list[dict[str, Any]]:
    """Forex Factory HTML scraper. Falls back when TradingEconomics is unavailable."""
    try:
        resp = httpx.get(FF_URL, headers=FF_HEADERS, timeout=TIMEOUT_SECONDS)
        resp.raise_for_status()
        events = parse_ff_response(resp.text)
        if not events:
            raise FetcherError("FF parse returned 0 events — DOM may have changed")
        return events
    except (httpx.HTTPError, ValueError, AttributeError, TypeError, KeyError) as e:
        raise FetcherError(f"FF fetch failed: {e}") from e


def write_cache_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", dir=str(path.parent), delete=False, suffix=".tmp"
    ) as tmp:
        json.dump(payload, tmp, indent=2)
        tmp_path = tmp.name
    os.replace(tmp_path, path)


def log_error(msg: str) -> None:
    try:
        ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
        with ERROR_LOG.open("a") as f:
            f.write(f"{datetime.now(CR_OFFSET).isoformat()} {msg}\n")
    except OSError as e:
        print(f"macro_calendar: could not write error log: {e}", file=sys.stderr)


def run(cache_path: Path) -> int:
    """Main fetch routine. Returns 0 on success, 1 on double failure."""
    source = None
    events: list[dict[str, Any]] = []
    try:
        events = fetch_te()
        source = "tradingeconomics"
    except FetcherError as te_err:
        log_error(f"TE failed: {te_err}; trying Forex Factory")
        try:
            events = fetch_ff()
            source = "forexfactory"
        except FetcherError as ff_err:
            log_error(f"FF also failed: {ff_err}; keeping existing cache")
            return 1

    payload = {
        "fetched_at": datetime.now(CR_OFFSET).isoformat(),
        "source": source,
        "events": events,
    }
    write_cache_atomic(cache_path, payload)
    print(f"macro_calendar: wrote {len(events)} events from {source} to {cache_path}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    p.add_argument("--refresh", action="store_true",
                   help="Alias for default behavior — refresh the macro events cache")
    args = p.parse_args()
    return run(args.cache)


if __name__ == "__main__":
    sys.exit(main())
