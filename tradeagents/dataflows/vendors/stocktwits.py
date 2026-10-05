"""StockTwits public symbol stream. No API key required.

A failed fetch is reported as ``<stocktwits unavailable>``, never as "no
messages": those are different claims and passing a rate-limited fetch off as
silence hands the sentiment analyst a signal that was never observed.
"""

from __future__ import annotations

import contextlib
import html
import http.client
import json
import logging
from datetime import datetime, timedelta
from urllib.request import Request, urlopen

from tradeagents.dataflows.symbols import crypto_base

logger = logging.getLogger(__name__)

_API = "https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
_UA = "tradeagents/0.2"


def _created_at(msg: dict) -> datetime | None:
    """Parse the StockTwits message creation timestamp, or return None if missing or invalid."""
    raw = msg.get("created_at")
    if not raw:
        return None
    with contextlib.suppress(ValueError, TypeError):
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    return None


def _symbol(ticker: str) -> str:
    """StockTwits lists crypto as ``BTC.X``; other symbols pass through upper-cased."""
    base = crypto_base(ticker)
    return f"{base}.X" if base else ticker.strip().upper()


def _in_window(dt: datetime | None, start_date: str, end_date: str) -> bool:
    """Half-open window ``[start, end + 1 day)``; naive vs aware is normalized."""
    if dt is None:
        return False
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
    return start <= dt < end


def fetch_stocktwits_messages(
    ticker: str,
    limit: int = 30,
    timeout: float = 10.0,
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    """Recent StockTwits messages for ``ticker`` as a plaintext block.

    Trimmed to ``[start_date, end_date]`` when given; a fetch failure is
    reported as unavailable rather than as silence.
    """
    url = _API.format(ticker=_symbol(ticker))
    req = Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except (OSError, http.client.HTTPException, json.JSONDecodeError) as exc:
        logger.warning("StockTwits fetch failed for %s: %s", ticker, exc)
        return f"<stocktwits unavailable: {type(exc).__name__}>"

    messages = data.get("messages", []) if isinstance(data, dict) else []
    if start_date and end_date:
        messages = [
            m for m in messages if _in_window(_created_at(m), start_date, end_date)
        ]
    if not messages:
        period = f" within {start_date}..{end_date}" if start_date else ""
        return f"<no StockTwits messages for ${ticker.upper()}{period}>"

    lines = []
    bull = bear = unlabeled = 0
    for m in messages[:limit]:
        created = m.get("created_at", "")
        user = (m.get("user") or {}).get("username", "?")
        sentiment_obj = (m.get("entities") or {}).get("sentiment") or {}
        sentiment = (
            sentiment_obj.get("basic") if isinstance(sentiment_obj, dict) else None
        )
        body = html.unescape(m.get("body") or "").replace("\n", " ").strip()
        if len(body) > 280:
            body = body[:280] + "…"
        if sentiment == "Bullish":
            bull += 1
            tag = "Bullish"
        elif sentiment == "Bearish":
            bear += 1
            tag = "Bearish"
        else:
            unlabeled += 1
            tag = "no-label"
        lines.append(f"[{created} · @{user} · {tag}] {body}")

    total = bull + bear + unlabeled
    summary = (
        f"Bullish: {bull} ({round(100 * bull / total)}%) · "
        f"Bearish: {bear} ({round(100 * bear / total)}%) · "
        f"Unlabeled: {unlabeled} · Total: {total} most-recent messages"
    )
    return summary + "\n\n" + "\n".join(lines)
