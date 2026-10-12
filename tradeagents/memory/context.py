"""Formatting settled entries into the ``past_context`` block the PM reads."""

from __future__ import annotations

from tradeagents.memory.log import DecisionLog


def build_past_context(
    log: DecisionLog,
    ticker: str,
    *,
    n_same: int = 5,
    n_cross: int = 3,
    as_of: str | None = None,
) -> str:
    """Recent lessons for the PM prompt: same-ticker decisions and cross-ticker lessons.

    ``as_of``, when given, filters to entries whose outcome was known by then —
    a historical run must not learn from an outcome that had not happened yet.
    A live run passes ``None`` and sees everything settled.
    """
    entries = [e for e in log.all_entries() if e.get("settled")]
    if as_of is not None:
        entries = [e for e in entries if e.get("resolved_date", "") <= as_of]
    if not entries:
        return ""

    # Most recent first; the log is in write order, which is roughly date order
    # but not exactly — an older trade_date can be settled later.
    entries.sort(key=lambda e: e["trade_date"], reverse=True)

    same = [e for e in entries if e["ticker"] == ticker][:n_same]
    cross = [e for e in entries if e["ticker"] != ticker][:n_cross]
    if not same and not cross:
        return ""

    parts: list[str] = []
    if same:
        parts.append(f"Past decisions on {ticker} (most recent first):")
        parts.extend(_format_full(e) for e in same)
    if cross:
        parts.append("Recent cross-ticker lessons:")
        parts.extend(_format_lesson(e) for e in cross)
    return "\n\n".join(parts)


def _format_full(entry: dict) -> str:
    """A same-ticker entry: full decision plus its reflection and outcome."""
    header = (
        f"[{entry['trade_date']} | {entry['rating']} | "
        f"{entry['raw_return']:+.1%} raw | {entry['alpha_return']:+.1%} alpha | "
        f"{entry['holding_days']}d vs {entry['benchmark']}]"
    )
    parts = [header, "DECISION:", entry.get("decision", "").strip()]
    if entry.get("reflection"):
        parts.append(f"REFLECTION:\n{entry['reflection'].strip()}")
    return "\n\n".join(parts)


def _format_lesson(entry: dict) -> str:
    """A cross-ticker entry: just the lesson, trimmed.

    The full decision on a different instrument is context the PM does not need;
    the reflection is the transferable part. When there is no reflection yet
    (should not happen for a settled entry, but tolerated), fall back to a
    truncated decision so the entry is not silent.
    """
    header = f"[{entry['trade_date']} | {entry['ticker']} | {entry['rating']}]"
    reflection = (entry.get("reflection") or "").strip()
    if reflection:
        return f"{header}\n{reflection}"
    decision = (entry.get("decision") or "").strip()[:300]
    suffix = "..." if len(entry.get("decision") or "") > 300 else ""
    return f"{header}\n{decision}{suffix}"
