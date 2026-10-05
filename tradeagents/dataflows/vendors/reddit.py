"""Reddit search via the public Atom/RSS feed (JSON search is WAF-blocked).

All configured subreddits are searched in one combined request. A failed
fetch is reported as unavailable; a rate limit backs off once.
"""

from __future__ import annotations

import html
import http.client
import logging
import re
import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

_RSS = "https://www.reddit.com/r/{sub}/search.rss?{qs}"
_UA = "tradeagents/0.2 (+https://github.com/A-janjan/trade-agent-plus)"
_ATOM = {"atom": "http://www.w3.org/2005/Atom"}
DEFAULT_SUBREDDITS = ("wallstreetbets", "stocks", "investing")
_FEED_PAGE = 100
_MAX_BYTES = 5 * 1024 * 1024
_RETRY_WAIT = 30.0


def _iso_to_ts(iso: str | None) -> float | None:
    """Convert an ISO 8601 string to a UTC timestamp, or return None if missing or invalid."""
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError):
        return None


def _strip_html(content: str) -> str:
    """Remove HTML tags and unescape HTML entities from a string."""
    if not content:
        return ""
    if "<!-- SC_OFF -->" in content and "<!-- SC_ON -->" in content:
        content = content.split("<!-- SC_OFF -->")[1].split("<!-- SC_ON -->")[0]
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", content)).split())


def _read_capped(resp) -> bytes:
    """Read up to ``_MAX_BYTES`` from a response, raising if the feed is too large."""
    data = resp.read(_MAX_BYTES + 1)
    if len(data) > _MAX_BYTES:
        raise http.client.HTTPException("feed too large")
    return data


def _fetch(
    ticker: str, subs: list[str], limit: int, timeout: float, _retry: bool = True
):
    """Return posts, or None on a fetch failure (distinct from an empty result)."""
    qs = urlencode(
        {"q": ticker, "restrict_sr": "on", "sort": "new", "t": "week", "limit": limit}
    )
    url = _RSS.format(sub="+".join(subs), qs=qs)
    req = Request(url, headers={"User-Agent": _UA})
    try:
        with urlopen(req, timeout=timeout) as resp:
            root = ET.fromstring(_read_capped(resp))
    except HTTPError as exc:
        if exc.code == 429 and _retry:
            logger.warning("Reddit 429 for %s; backing off %.0fs", ticker, _RETRY_WAIT)
            time.sleep(_RETRY_WAIT)
            return _fetch(ticker, subs, limit, timeout, _retry=False)
        logger.warning("Reddit fetch failed: %s", exc)
        return None
    except (OSError, http.client.HTTPException, ET.ParseError) as exc:
        logger.warning("Reddit fetch failed: %s", exc)
        return None

    posts = []
    for entry in root.findall("atom:entry", _ATOM)[:limit]:
        title_el = entry.find("atom:title", _ATOM)
        pub_el = entry.find("atom:published", _ATOM)
        content_el = entry.find("atom:content", _ATOM)
        category_el = entry.find("atom:category", _ATOM)
        posts.append(
            {
                "title": (title_el.text if title_el is not None else "") or "",
                "created_utc": _iso_to_ts(pub_el.text if pub_el is not None else None),
                "selftext": _strip_html(
                    (content_el.text or "") if content_el is not None else ""
                ),
                "subreddit": category_el.get("term") if category_el is not None else "",
            }
        )
    return posts


def fetch_reddit_posts(
    ticker: str,
    subreddits=DEFAULT_SUBREDDITS,
    *,
    limit_per_sub: int = 5,
    timeout: float = 10.0,
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    """Recent Reddit posts mentioning ``ticker`` across finance subreddits."""
    subs = list(subreddits)
    label = ", ".join(f"r/{s}" for s in subs)
    fetched = _fetch(ticker, subs, _FEED_PAGE, timeout)
    if fetched is None:
        return f"<Reddit unavailable: fetch failed ({label}); this is not an absence of discussion>"

    if start_date and end_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        posts = [
            p
            for p in fetched
            if p["created_utc"]
            and start_dt
            <= datetime.fromtimestamp(p["created_utc"], tz=UTC).replace(
                tzinfo=None
            )
            < end_dt
        ]
    else:
        posts = fetched

    if not posts:
        period = (
            f" within {start_date}..{end_date}" if start_date else " in the past 7 days"
        )
        return f"<no Reddit posts mentioning {ticker.upper()} across {label}{period}>"

    # Group back by subreddit for readability.
    by_sub: dict[str, tuple[str, list[dict]]] = {s.lower(): (s, []) for s in subs}
    for p in posts:
        sub = p.get("subreddit") or (subs[0] if len(subs) == 1 else "unknown")
        by_sub.setdefault(sub.lower(), (sub, []))[1].append(p)

    blocks = []
    for sub, sub_posts in by_sub.values():
        if not sub_posts:
            blocks.append(f"r/{sub}: <no posts found mentioning {ticker.upper()}>")
            continue
        sub_posts = sub_posts[:limit_per_sub]
        lines = [
            f"r/{sub} — {len(sub_posts)} recent posts mentioning {ticker.upper()}:"
        ]
        for p in sub_posts:
            title = (p.get("title") or "").replace("\n", " ").strip()
            created = p.get("created_utc")
            date_str = (
                datetime.fromtimestamp(created, tz=UTC).strftime("%Y-%m-%d")
                if created
                else "?"
            )
            body = (p.get("selftext") or "").replace("\n", " ").strip()
            if len(body) > 240:
                body = body[:240] + "…"
            lines.append(
                f"  [{date_str}] {title}"
                + (f"\n    body excerpt: {body}" if body else "")
            )
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)
