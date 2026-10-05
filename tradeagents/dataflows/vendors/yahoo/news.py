"""Yahoo Finance ticker-specific and global news, with look-ahead-safe windows."""

from __future__ import annotations

import contextlib
import logging
from datetime import UTC, datetime, timedelta

import yfinance as yf

from tradeagents.dataflows.config import get_config
from tradeagents.dataflows.errors import NoMarketDataError
from tradeagents.dataflows.symbols import normalize_symbol
from tradeagents.dataflows.vendors.yahoo.ohlcv import yf_retry

logger = logging.getLogger(__name__)


def _extract(article: dict) -> dict:
    """Normalize a Yahoo news article across the two payload shapes it uses."""
    if "content" in article:
        c = article["content"]
        provider = (c.get("provider") or {}).get("displayName", "Unknown")
        url_obj = c.get("canonicalUrl") or c.get("clickThroughUrl") or {}
        pub = None
        pub_str = c.get("pubDate", "")
        if pub_str:
            with contextlib.suppress(ValueError, AttributeError):
                pub = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
        return {
            "title": c.get("title", "No title"),
            "summary": c.get("summary", ""),
            "publisher": provider,
            "link": url_obj.get("url", ""),
            "pub_date": pub,
        }
    pub = None
    ts = article.get("providerPublishTime")
    if ts:
        with contextlib.suppress(ValueError, OSError, TypeError):
            pub = datetime.fromtimestamp(ts, tz=UTC)
    return {
        "title": article.get("title", "No title"),
        "summary": article.get("summary", ""),
        "publisher": article.get("publisher", "Unknown"),
        "link": article.get("link", ""),
        "pub_date": pub,
    }


def _in_window(dt, start_dt: datetime, end_dt: datetime) -> bool:
    """Half-open window ``[start, end + 1 day)``; naive vs aware is normalized.

    An undated article is kept only when the window reaches the present, so a
    backtest never sees a piece whose publication date nobody observed.
    """
    end = end_dt + timedelta(days=1)
    if dt is None:
        return end.date() >= datetime.utcnow().date() - timedelta(days=1)
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    return start_dt <= dt < end


def _render(articles: list[dict], header: str) -> str:
    parts = [header, ""]
    for a in articles:
        parts.append(f"### {a['title']} (source: {a['publisher']})")
        if a["summary"]:
            parts.append(a["summary"])
        if a["link"]:
            parts.append(f"Link: {a['link']}")
        parts.append("")
    return "\n".join(parts)


def get_news(ticker: str, start_date: str, end_date: str) -> str:
    """Ticker-specific news within ``[start_date, end_date]``."""
    limit = get_config().get("news_article_limit", 20)
    canonical = normalize_symbol(ticker)
    try:
        articles = yf_retry(lambda: yf.Ticker(canonical).get_news(count=limit)) or []
    except Exception as e:
        raise NoMarketDataError(ticker, canonical, f"news unavailable: {e}") from e

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    kept = [
        a
        for a in (_extract(x) for x in articles)
        if _in_window(a["pub_date"], start_dt, end_dt)
    ]
    if not kept:
        return f"No news found for {ticker} between {start_date} and {end_date}"
    return _render(kept, f"## {ticker} news, {start_date} to {end_date}")


def get_global_news(
    curr_date: str, look_back_days: int | None = None, limit: int | None = None
) -> str:
    """Global macro news from configured search queries within the trailing window."""
    cfg = get_config()
    if look_back_days is None:
        look_back_days = cfg.get("global_news_lookback_days", 7)
    if look_back_days is None:
        look_back_days = 7
    if limit is None:
        limit = cfg.get("global_news_article_limit", 10)
    if limit is None:
        limit = 10
    queries = cfg.get("global_news_queries") or [
        "Federal Reserve interest rates inflation"
    ]

    curr_dt = datetime.strptime(curr_date, "%Y-%m-%d")
    start_dt = curr_dt - timedelta(days=look_back_days)

    seen_titles: set[str] = set()
    kept: list[dict] = []
    for q in queries:
        try:
            search = yf_retry(
                lambda qq=q: yf.Search(
                    query=qq, news_count=limit, enable_fuzzy_query=True
                )
            )
        except Exception as e:
            logger.warning("Global news search failed for %r: %s", q, e)
            continue
        if search is None:
            continue
        for art in search.news or []:
            a = _extract(art)
            if not _in_window(a["pub_date"], start_dt, curr_dt):
                continue
            if a["title"] and a["title"] not in seen_titles:
                seen_titles.add(a["title"])
                kept.append(a)
        if len(kept) >= limit:
            break

    if not kept:
        return f"No global news found between {start_dt.strftime('%Y-%m-%d')} and {curr_date}"
    return _render(
        kept[:limit],
        f"## Global market news, {start_dt.strftime('%Y-%m-%d')} to {curr_date}",
    )
