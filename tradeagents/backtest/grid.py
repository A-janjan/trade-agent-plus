"""Turn a start date, an end date, and a step into the dates a sweep will run.

The grid stops at today: a future date has no outcome to settle against, and
the graph itself rejects one. Sampling is by calendar days, not trading days —
the point of the grid is to pick different decision dates, and a weekend
decision is as meaningful a test as any other.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from tradeagents.dataflows.date_window import get_current_date


def _parse(date_str: str, what: str) -> datetime:
    """Parse a grid bound, rejecting anything the graph's date validator would."""
    try:
        parsed = datetime.strptime(str(date_str), "%Y-%m-%d")
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{what} must be a date in YYYY-MM-DD format, got {date_str!r}"
        ) from exc
    if parsed.strftime("%Y-%m-%d") != str(date_str):
        raise ValueError(f"{what} must be canonical YYYY-MM-DD, got {date_str!r}")
    return parsed


def iter_grid(start: str, end: str, every_n_days: int = 1) -> list[str]:
    """Analysis dates from ``start`` to ``end`` inclusive, stepped by ``every_n_days``.

    The last date is clamped to today. An empty result (a range entirely in
    the future) is not an error — a caller may legitimately ask about a future
    window and learn there is nothing to sweep — but the error message on a
    reversed range says so plainly instead of returning silently.
    """
    if every_n_days < 1:
        raise ValueError(f"every_n_days must be at least 1, got {every_n_days}")

    start_dt = _parse(start, "start")
    end_dt = _parse(end, "end")
    if end_dt < start_dt:
        raise ValueError(f"end ({end}) is before start ({start})")

    last = min(end_dt, datetime.strptime(get_current_date(), "%Y-%m-%d"))
    if last < start_dt:
        return []

    dates: list[str] = []
    cursor = start_dt
    while cursor <= last:
        dates.append(cursor.strftime("%Y-%m-%d"))
        cursor += timedelta(days=every_n_days)
    return dates
