"""Alpha Vantage NEWS_SENTIMENT, ticker-filtered and window-filtered.

Alpha Vantage tags each article with per-ticker sentiment scores. This module
keeps the sentiment as part of the article, so a downstream reader sees both
the headline and Alpha Vantage's read of it.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from tradeagents.dataflows.config import get_config
from tradeagents.dataflows.errors import NoMarketDataError
from tradeagents.dataflows.vendors.alpha_vantage._http import request


def _stamp(date_str: str, *, end_of_day: bool = False) -> str:
    """Alpha Vantage wants ``YYYYMMDDTHHMM``; midnight or 23:59 for the bounds."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime("%Y%m%dT2359" if end_of_day else "%Y%m%dT0000")


def get_news(ticker: str, start_date: str, end_date: str) -> str:
    """Ticker-specific news in the window, with Alpha Vantage's sentiment tags."""
    limit = get_config().get("news_article_limit", 20)
    text = request(
        "NEWS_SENTIMENT",
        symbol=ticker,
        tickers=ticker,  # NEWS_SENTIMENT uses `tickers`, not `symbol`; both included
        time_from=_stamp(start_date),
        time_to=_stamp(end_date, end_of_day=True),
        limit=str(limit),
    )
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise NoMarketDataError(ticker, ticker, f"unparseable response: {exc}") from exc

    feed = payload.get("feed") or []
    if not feed:
        return f"No news found for {ticker} between {start_date} and {end_date}"

    parts = [f"## {ticker} news, {start_date} to {end_date}", ""]
    for a in feed:
        parts.append(
            f"### {a.get('title', 'No title')} (source: {a.get('source', 'Unknown')})"
        )
        if a.get("summary"):
            parts.append(a["summary"])
        # Per-ticker sentiment for the ticker we asked about, if Alpha Vantage
        # returned one.
        for tag in a.get("ticker_sentiment", []):
            if tag.get("ticker", "").upper() == ticker.upper():
                parts.append(
                    f"Sentiment: {tag.get('ticker_sentiment_label', '?')} "
                    f"(score {tag.get('ticker_sentiment_score', '?')})"
                )
        if a.get("url"):
            parts.append(f"Link: {a['url']}")
        parts.append("")
    return "\n".join(parts)


def get_global_news(
    curr_date: str, look_back_days: int | None = None, limit: int | None = None
) -> str:
    """Broad macro news across a fixed set of topics."""
    cfg = get_config()
    if look_back_days is None:
        look_back_days = int(cfg.get("global_news_lookback_days", 7))
    if limit is None:
        limit = cfg.get("global_news_article_limit", 10)

    end_dt = datetime.strptime(curr_date, "%Y-%m-%d")
    start_dt = end_dt - timedelta(days=look_back_days)

    text = request(
        "NEWS_SENTIMENT",
        symbol="",  # NEWS_SENTIMENT accepts an empty symbol when topics are given
        topics="financial_markets,economy_macro,economy_monetary",
        time_from=start_dt.strftime("%Y%m%dT0000"),
        time_to=end_dt.strftime("%Y%m%dT2359"),
        limit=str(limit),
    )
    payload = json.loads(text)
    feed = payload.get("feed") or []
    if not feed:
        return f"No global news found between {start_dt.strftime('%Y-%m-%d')} and {curr_date}"

    parts = [
        f"## Global market news, {start_dt.strftime('%Y-%m-%d')} to {curr_date}",
        "",
    ]
    for a in feed:
        parts.append(
            f"### {a.get('title', 'No title')} (source: {a.get('source', 'Unknown')})"
        )
        if a.get("summary"):
            parts.append(a["summary"])
        if a.get("url"):
            parts.append(f"Link: {a['url']}")
        parts.append("")
    return "\n".join(parts)
