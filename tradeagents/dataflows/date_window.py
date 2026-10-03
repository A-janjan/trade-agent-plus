"""Shared date helpers for run-scoped time bounds.

Every dated tool call is clamped to the run's ``trade_date`` so a model can't
walk past the point-in-time cutoff the rest of the pipeline enforces.
"""

from __future__ import annotations

from datetime import date, datetime


def get_current_date() -> str:
    """Today's date, YYYY-MM-DD."""
    return date.today().strftime("%Y-%m-%d")


def as_of(requested: str | None, trade_date: str) -> str | None:
    """The date a tool serves: the requested date, but never past ``trade_date``.

    A model can omit the date or pass today's instead of the analysis date,
    which would walk past every point-in-time guard behind the tool. An empty
    ``trade_date`` (a direct call outside a graph run) passes the request
    through unchanged.
    """
    if not trade_date:
        return requested
    try:
        cutoff = datetime.strptime(trade_date, "%Y-%m-%d")
    except ValueError:
        return requested
    if not requested:
        return trade_date
    try:
        parsed = datetime.strptime(requested, "%Y-%m-%d")
    except ValueError:
        return trade_date
    return requested if parsed <= cutoff else trade_date
