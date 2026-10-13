"""SEC EDGAR: statements as they were filed.

Every other fundamentals vendor serves a period's current value, cut at the
fiscal period end. That is two claims a run should not make: a period that
has ended is not public until the company files (weeks later), and a figure
that was later restated is not what investors saw at the time.

EDGAR reports every fact with the date it was filed, so a run dated
``curr_date`` serves exactly what was on file by then. No key or account:
SEC requires only a User-Agent identifying the caller, which this module
reads from ``SEC_EDGAR_USER_AGENT`` (falling back to a package default).
US filers only; anything not in EDGAR's ticker map falls through to the next
vendor in the chain.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import date
from pathlib import Path

import requests

from tradeagents.dataflows.config import get_config
from tradeagents.dataflows.errors import NoMarketDataError, VendorRateLimitError

logger = logging.getLogger(__name__)

_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

# A filing history changes only when something new is filed, so one fetch per
# day serves every date a run asks about.
_CACHE_TTL_SECONDS = 24 * 60 * 60
_TIMEOUT = 30.0

# Each line item: a friendly label and the XBRL tags filers use, best first.
# The first tag that reports a period wins; values are never summed across
# tags, which would double-count a company that reports revenue under two.
_LINES: dict[str, list[tuple[str, tuple[str, ...]]]] = {
    "balance_sheet": [
        ("Total Assets", ("Assets",)),
        ("Current Assets", ("AssetsCurrent",)),
        ("Cash and Equivalents", ("CashAndCashEquivalentsAtCarryingValue",)),
        ("Total Liabilities", ("Liabilities",)),
        ("Current Liabilities", ("LiabilitiesCurrent",)),
        (
            "Stockholders' Equity",
            (
                "StockholdersEquity",
                "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
            ),
        ),
    ],
    "income": [
        (
            "Revenue",
            (
                "RevenueFromContractWithCustomerExcludingAssessedTax",
                "Revenues",
                "SalesRevenueNet",
            ),
        ),
        ("Cost of Revenue", ("CostOfRevenue", "CostOfGoodsAndServicesSold")),
        ("Gross Profit", ("GrossProfit",)),
        ("Operating Income", ("OperatingIncomeLoss",)),
        ("Net Income", ("NetIncomeLoss",)),
        ("Diluted EPS", ("EarningsPerShareDiluted",)),
    ],
    "cashflow": [
        (
            "Operating Cash Flow",
            (
                "NetCashProvidedByUsedInOperatingActivities",
                "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
            ),
        ),
        ("Investing Cash Flow", ("NetCashProvidedByUsedInInvestingActivities",)),
        ("Financing Cash Flow", ("NetCashProvidedByUsedInFinancingActivities",)),
        (
            "Capital Expenditure",
            (
                "PaymentsToAcquirePropertyPlantAndEquipment",
                "PaymentsToAcquireProductiveAssets",
            ),
        ),
    ],
}

# A statement's figures cover a span: a quarter is about 90 days, a year about
# 365. One filing reports both the quarter and the year to date under the same
# end date, so a match on the end date alone can report half a year as a quarter.
_SPANS = {"quarterly": (60, 115), "annual": (300, 400)}


def _user_agent() -> str:
    """Who SEC sees. SEC refuses a User-Agent with no contact address."""
    configured = os.environ.get("SEC_EDGAR_USER_AGENT", "").strip()
    return configured or "tradeagents/0.1 (contact@example.com)"


def _fetch(url: str) -> dict:
    try:
        response = requests.get(
            url, headers={"User-Agent": _user_agent()}, timeout=_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        # Any failure here is "vendor cannot serve it now"; the router moves on.
        raise VendorRateLimitError(
            f"SEC EDGAR request failed: {type(exc).__name__}"
        ) from exc
    except ValueError as exc:
        raise VendorRateLimitError("SEC EDGAR returned unreadable JSON") from exc


def _cached(url: str, name: str) -> dict:
    """One fetch per company per day, cached under the configured cache dir."""
    path = Path(get_config()["data_cache_dir"]) / "sec_edgar" / name
    if path.exists() and time.time() - path.stat().st_mtime < _CACHE_TTL_SECONDS:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            pass  # a truncated file is a miss, not a failure
    data = _fetch(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
    os.replace(tmp, path)
    return data


def _cik(ticker: str) -> str | None:
    """The filer's CIK, or None when the ticker is not a US filer."""
    table = _cached(_TICKERS_URL, "company_tickers.json")
    wanted = ticker.strip().upper()
    for entry in table.values():
        if entry.get("ticker", "").upper() == wanted:
            return f"{int(entry['cik_str']):010d}"
    return None


def _as_of(
    facts: dict,
    tags: tuple[str, ...],
    curr_date: str,
    span: tuple[int, int],
) -> tuple[dict[str, float], str]:
    """({period end: value}, unit) for the first tag the filer reports, as known then.

    When a period appears more than once (restatements), the latest filing on
    or before the cutoff wins, so an amendment counts from the day it was filed
    and not before. The unit comes from the filing: most lines are USD, EPS is
    USD/shares, and scaling both alike would print a real figure as zero.
    """
    low, high = span
    values: dict[str, float] = {}
    unit = "USD"
    for tag in tags:
        series = (facts.get(tag) or {}).get("units", {})
        for u, entries in series.items():
            latest: dict[str, dict] = {}
            for fact in entries:
                if fact["filed"] > curr_date or fact["end"] in values:
                    continue
                if "start" in fact:
                    days = (
                        date.fromisoformat(fact["end"])
                        - date.fromisoformat(fact["start"])
                    ).days
                    if not low <= days <= high:
                        continue
                seen = latest.get(fact["end"])
                if seen is None or fact["filed"] >= seen["filed"]:
                    latest[fact["end"]] = fact
            if latest:
                unit = u
                values.update({end: fact["val"] for end, fact in latest.items()})
    return dict(sorted(values.items())), unit


def _statement(
    kind: str, ticker: str, freq: str, curr_date: str | None, title: str
) -> str:
    curr_date = curr_date or date.today().isoformat()
    cik = _cik(ticker)
    if cik is None:
        raise NoMarketDataError(ticker, ticker, "not a US SEC filer")
    facts_payload = _cached(_FACTS_URL.format(cik=cik), f"CIK{cik}.json")
    us_gaap = (facts_payload.get("facts") or {}).get("us-gaap")
    if not us_gaap:
        raise NoMarketDataError(ticker, ticker, "no us-gaap facts on file")

    span = _SPANS["quarterly" if freq.lower() == "quarterly" else "annual"]
    lines = {
        label: _as_of(us_gaap, tags, curr_date, span) for label, tags in _LINES[kind]
    }
    periods = sorted({p for values, _ in lines.values() for p in values})
    if not periods:
        raise NoMarketDataError(
            ticker, ticker, f"no {freq} {title.lower()} filed by {curr_date}"
        )

    header = (
        f"# {title} for {ticker.upper()} ({freq})\n"
        f"# SEC EDGAR facts filed on or before {curr_date}, as filed then\n"
        f"# USD in millions unless the row says otherwise\n\n"
    )
    # CSV, with every row spanning the same periods, so a reader can diff
    # across columns and a script can parse without a markdown parser.
    rows = [",".join([""] + periods)]
    for label, (values, unit) in lines.items():
        if not values:
            rows.append(",".join([label] + ["unavailable"] * len(periods)))
            continue
        name = label if unit == "USD" else f"{label} ({unit})"
        cells = [
            (
                (f"{values[p] / 1e6:.0f}" if unit == "USD" else f"{values[p]:.2f}")
                if p in values
                else ""
            )
            for p in periods
        ]
        rows.append(",".join([name] + cells))
    return header + "\n".join(rows) + "\n"


def get_balance_sheet(
    ticker: str, freq: str = "quarterly", curr_date: str | None = None
) -> str:
    return _statement("balance_sheet", ticker, freq, curr_date, "Balance Sheet")


def get_income_statement(
    ticker: str, freq: str = "quarterly", curr_date: str | None = None
) -> str:
    return _statement("income", ticker, freq, curr_date, "Income Statement")


def get_cashflow(
    ticker: str, freq: str = "quarterly", curr_date: str | None = None
) -> str:
    return _statement("cashflow", ticker, freq, curr_date, "Cash Flow Statement")
