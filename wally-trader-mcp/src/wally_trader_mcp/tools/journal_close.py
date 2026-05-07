"""journal_close tool — compute end-of-day metrics + append journal entry + equity row."""
from __future__ import annotations

from dataclasses import asdict
from datetime import date as _date
from typing import Optional

from wally_core.memory import get_backend, JournalEntry, EquityRow
from wally_core.journal import compute_metrics


def journal_close(
    profile: str,
    summary: str,
    lessons: str = "",
    trades: Optional[list[dict]] = None,
    equity_usd: Optional[float] = None,
    daily_pnl_usd: float = 0.0,
) -> dict:
    """Close out a trading day for a profile.

    Steps:
        1. Computes metrics from trades list (if provided)
        2. Writes JournalEntry markdown
        3. Appends EquityRow if equity_usd provided

    Args:
        profile: trading profile name
        summary: human-readable session summary
        lessons: lessons learned or empty string
        trades: optional list of trade dicts (each must have 'pnl_usd'; optionally 'score')
        equity_usd: current equity in USD (required to append equity row)
        daily_pnl_usd: net PnL for the day in USD (used to compute daily_return_pct)

    Returns:
        dict with profile, date, metrics (or None), journal_written, equity_appended
    """
    today = _date.today().isoformat()
    backend = get_backend(profile)

    metrics = None
    if trades:
        try:
            m = compute_metrics(trades)
            metrics = asdict(m)
        except Exception as exc:
            metrics = {"error": str(exc)}

    entry = JournalEntry(
        profile=profile,
        date=today,
        summary=summary,
        lessons=lessons,
    )
    backend.append_journal(profile, entry)

    equity_appended = False
    if equity_usd is not None:
        prev_equity = equity_usd - daily_pnl_usd
        daily_return_pct = (daily_pnl_usd / prev_equity * 100) if prev_equity else 0.0
        backend.append_equity(
            profile,
            EquityRow(
                profile=profile,
                date=today,
                equity_usd=equity_usd,
                daily_pnl_usd=daily_pnl_usd,
                daily_return_pct=round(daily_return_pct, 4),
            ),
        )
        equity_appended = True

    return {
        "profile": profile,
        "date": today,
        "metrics": metrics,
        "journal_written": True,
        "equity_appended": equity_appended,
    }
