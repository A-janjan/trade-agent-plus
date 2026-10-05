"""Yahoo Finance fundamentals: overview, statements.

Statements are cut at ``curr_date`` by fiscal period end. Yahoo does not carry
filing dates, so the newest period may postdate the analysis date; the header
says so rather than implying a stricter guarantee.
"""

from __future__ import annotations

import logging

import pandas as pd
import yfinance as yf

from tradeagents.dataflows.errors import NoMarketDataError, VendorError
from tradeagents.dataflows.symbols import normalize_symbol
from tradeagents.dataflows.vendors.yahoo.ohlcv import raise_for_empty, yf_retry

logger = logging.getLogger(__name__)

_PERIOD_END_VINTAGE = (
    "# Periods are cut at fiscal period end. Yahoo does not report filing "
    "dates, so the newest period may not have been published yet on this date.\n\n"
)

_OVERVIEW_FIELDS = [
    ("Name", "longName"),
    ("Sector", "sector"),
    ("Industry", "industry"),
    ("Market Cap", "marketCap"),
    ("PE (TTM)", "trailingPE"),
    ("Forward PE", "forwardPE"),
    ("PEG", "pegRatio"),
    ("Price / Book", "priceToBook"),
    ("EPS (TTM)", "trailingEps"),
    ("Forward EPS", "forwardEps"),
    ("Dividend Yield", "dividendYield"),
    ("Beta", "beta"),
    ("52W High", "fiftyTwoWeekHigh"),
    ("52W Low", "fiftyTwoWeekLow"),
    ("50D Avg", "fiftyDayAverage"),
    ("200D Avg", "twoHundredDayAverage"),
    ("Revenue (TTM)", "totalRevenue"),
    ("Gross Profit", "grossProfits"),
    ("EBITDA", "ebitda"),
    ("Net Income", "netIncomeToCommon"),
    ("Profit Margin", "profitMargins"),
    ("Operating Margin", "operatingMargins"),
    ("ROE", "returnOnEquity"),
    ("ROA", "returnOnAssets"),
    ("Debt / Equity", "debtToEquity"),
    ("Current Ratio", "currentRatio"),
    ("Book Value", "bookValue"),
    ("Free Cash Flow", "freeCashflow"),
]


def get_fundamentals(ticker: str, curr_date: str | None = None) -> str:
    """Company overview: profile, valuation, margins, key financials."""
    canonical = normalize_symbol(ticker)
    try:
        info = yf_retry(lambda: yf.Ticker(canonical).info) or {}
    except VendorError:
        raise
    except Exception as e:
        raise NoMarketDataError(
            ticker, canonical, f"fundamentals unavailable: {e}"
        ) from e

    lines = [
        f"{label}: {info[key]}"
        for label, key in _OVERVIEW_FIELDS
        if info.get(key) is not None
    ]
    if not lines:
        raise NoMarketDataError(ticker, canonical, "no fundamental fields returned")
    return f"# Company fundamentals for {canonical}\n\n" + "\n".join(lines)


def _filter_columns(df: pd.DataFrame, curr_date: str | None) -> pd.DataFrame:
    """Drop statement columns (fiscal period timestamps) after ``curr_date``."""
    if not curr_date or df.empty:
        return df
    cutoff = pd.Timestamp(curr_date)
    mask = pd.to_datetime(df.columns, errors="coerce") <= cutoff
    return df.loc[:, mask]


def _statement(
    ticker: str,
    freq: str,
    curr_date: str | None,
    attr_q: str,
    attr_a: str,
    title: str,
) -> str:
    """Get a financial statement (balance sheet, cash flow, income statement)."""
    canonical = normalize_symbol(ticker)
    try:
        tk = yf.Ticker(canonical)
        attr = attr_q if freq.lower() == "quarterly" else attr_a
        df = yf_retry(lambda: getattr(tk, attr))
    except VendorError:
        raise
    except Exception as e:
        raise NoMarketDataError(
            ticker, canonical, f"{title.lower()} unavailable: {e}"
        ) from e

    if df is None or df.empty:
        raise_for_empty(ticker, canonical, title.lower())
    df = _filter_columns(df, curr_date)
    if df.empty:
        raise NoMarketDataError(
            ticker, canonical, f"no {freq} {title.lower()} on or before {curr_date}"
        )
    return f"# {title} for {canonical} ({freq})\n" + _PERIOD_END_VINTAGE + df.to_csv()


def get_balance_sheet(
    ticker: str, freq: str = "quarterly", curr_date: str | None = None
) -> str:
    return _statement(
        ticker,
        freq,
        curr_date,
        "quarterly_balance_sheet",
        "balance_sheet",
        "Balance Sheet",
    )


def get_cashflow(
    ticker: str, freq: str = "quarterly", curr_date: str | None = None
) -> str:
    return _statement(
        ticker, freq, curr_date, "quarterly_cashflow", "cashflow", "Cash Flow"
    )


def get_income_statement(
    ticker: str, freq: str = "quarterly", curr_date: str | None = None
) -> str:
    return _statement(
        ticker,
        freq,
        curr_date,
        "quarterly_income_stmt",
        "income_stmt",
        "Income Statement",
    )
