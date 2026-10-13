"""Polymarket prediction markets.

Live, market-implied probabilities for forward-looking events — Fed decisions,
recession, elections, geopolitics. Complements news ("what happened") and
FRED ("where things stand") with "what the crowd prices next".

Polymarket serves only live odds on open markets, with no historical vintage;
a past run is told so rather than being served today's prices as if they were
known then. No API key.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

import requests

from tradeagents.dataflows.date_window import get_current_date

logger = logging.getLogger(__name__)

_BASE = "https://gamma-api.polymarket.com"
_TIMEOUT = 30.0
_DEFAULT_LIMIT = 6


def _parse_list(value) -> list:
    """Gamma returns ``outcomes`` and ``outcomePrices`` as JSON-encoded strings."""
    if isinstance(value, list):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


def _forward_looking(market: dict, now: datetime) -> bool:
    """Whether a market is open and resolves in the future."""
    if market.get("closed"):
        return False
    end = market.get("endDate")
    if end:
        try:
            if datetime.fromisoformat(end.replace("Z", "+00:00")) < now:
                return False
        except ValueError:
            pass
    # A market with no outcomes or no prices cannot be ranked or displayed.
    return bool(_parse_list(market.get("outcomes"))) and bool(
        _parse_list(market.get("outcomePrices"))
    )


def get_prediction_markets(topic: str, curr_date: str, limit: int | None = None) -> str:
    """Open markets matching ``topic``, ranked by traded volume."""
    if curr_date < get_current_date():
        return (
            f"Prediction-market odds are withheld for {curr_date}: Polymarket "
            f"serves only live odds, with no historical vintage, so serving "
            f"today's prices would leak post-decision information."
        )
    if limit is None:
        limit = _DEFAULT_LIMIT

    try:
        response = requests.get(
            f"{_BASE}/public-search",
            params={"q": topic, "limit_per_type": 20},
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Polymarket search failed for %r: %s", topic, exc)
        return (
            f"Polymarket is unreachable ({type(exc).__name__}); proceed without "
            f"prediction-market signal for {topic!r}."
        )

    now = datetime.now(UTC)
    candidates = [
        m
        for event in data.get("events", [])
        for m in event.get("markets", [])
        if _forward_looking(m, now)
    ]
    candidates.sort(key=lambda m: m.get("volumeNum") or 0, reverse=True)

    header = (
        f'## Polymarket: "{topic}"\n'
        f"Live, market-implied probabilities. A probability is the crowd's "
        f"priced odds of the event, not a forecast to treat as certain.\n\n"
    )
    if not candidates:
        return header + (
            f"No open markets matched {topic!r}. Coverage is concentrated in "
            f"macro, political, geopolitical, and crypto events."
        )

    lines: list[str] = []
    for m in candidates[:limit]:
        prices = _parse_list(m.get("outcomePrices"))
        outcomes = _parse_list(m.get("outcomes"))
        try:
            prob = float(prices[0])
        except (ValueError, IndexError):
            continue
        label = outcomes[0] if outcomes else "Yes"
        volume = m.get("volumeNum") or 0
        end_date = (m.get("endDate") or "")[:10]
        week = m.get("oneWeekPriceChange")
        week_str = (
            f", 1w {week * 100:+.1f}pp"
            if isinstance(week, (int, float)) and week
            else ""
        )
        lines.append(
            f"- **{m.get('question')}** — {label} {prob:.0%} "
            f"(${volume:,.0f} volume, resolves {end_date}{week_str})"
        )
    return header + "\n".join(lines) + "\n"
