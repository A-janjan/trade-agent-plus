"""Alpha Vantage fundamentals: overview and statements.

The statements are point-in-time: each report carries ``fiscalDateEnding``,
and reports dated after the analysis date are dropped. The overview
(``OVERVIEW``) is a present-day snapshot with no vintage; it is withheld for
a historical run rather than leaking post-decision values into a backtest.
"""

from __future__ import annotations

import json
from datetime import datetime

from tradeagents.dataflows.vendors.alpha_vantage._http import request

# Overview fields this system exposes; anything else stays out so the output
# is bounded and consistent across runs.
_OVERVIEW_FIELDS = (
    ("Name", "Name"),
    ("Sector", "Sector"),
    ("Industry", "Industry"),
    ("Market Cap", "MarketCapitalization"),
    ("PE (TTM)", "PERatio"),
    ("Forward PE", "ForwardPE"),
    ("PEG", "PEGRatio"),
    ("Price / Book", "PriceToBookRatio"),
    ("EPS (TTM)", "EPS"),
    ("Dividend Yield", "DividendYield"),
    ("Beta", "Beta"),
    ("52W High", "52WeekHigh"),
    ("52W Low", "52WeekLow"),
    ("50D Avg", "50DayMovingAverage"),
    ("200D Avg", "200DayMovingAverage"),
    ("Revenue (TTM)", "RevenueTTM"),
    ("Gross Profit (TTM)", "GrossProfitTTM"),
    ("Profit Margin", "ProfitMargin"),
    ("Operating Margin", "OperatingMarginTTM"),
    ("ROE", "ReturnOnEquityTTM"),
    ("ROA", "ReturnOnAssetsTTM"),
    ("Quarterly Earnings Growth", "QuarterlyEarningsGrowthYOY"),
    ("Quarterly Revenue Growth", "QuarterlyRevenueGrowthYOY"),
)


def _historical_notice(ticker: str, curr_date: str) -> str:
    """The notice to serve instead of the present-day overview, on a past run."""
    return (
        f"# Company fundamentals for {ticker}\n"
        f"# Point-in-time as of: {curr_date}\n\n"
        f"The overview snapshot is withheld: it carries no historical vintage. "
        f"Serving today's valuation and 52-week range into a {curr_date} analysis "
        f"would put post-decision information into the run. Point-in-time "
        f"fundamentals come from the statement endpoints (balance sheet, income, "
        f"cash flow), which carry filing dates."
    )


def get_fundamentals(ticker: str, curr_date: str | None = None) -> str:
    """Company overview; withheld for a past analysis date."""
    if curr_date and curr_date < datetime.now().strftime("%Y-%m-%d"):
        return _historical_notice(ticker, curr_date)

    text = request("OVERVIEW", symbol=ticker)
    payload = json.loads(text)
    if not payload or payload.get("Symbol") is None:
        # Alpha Vantage returns {} or a notice for an unknown symbol; the
        # notice path already raised, so a bare {} means "not covered".
        from tradeagents.dataflows.errors import NoMarketDataError

        raise NoMarketDataError(ticker, ticker, "no overview returned")

    lines = [
        f"{label}: {payload[src]}"
        for label, src in _OVERVIEW_FIELDS
        if payload.get(src) not in (None, "None", "-")
    ]
    if not lines:
        from tradeagents.dataflows.errors import NoMarketDataError

        raise NoMarketDataError(ticker, ticker, "no usable overview fields")
    return f"# Company fundamentals for {ticker}\n\n" + "\n".join(lines)


def _statement(
    endpoint: str,
    ticker: str,
    curr_date: str | None,
    title: str,
) -> str:
    """A statement endpoint, trimmed to reports filed by ``curr_date``."""
    text = request(endpoint, symbol=ticker)
    payload = json.loads(text)

    # Both keys name the same list — Alpha Vantage has used both across
    # quarters. Take whichever is present.
    reports = payload.get("quarterlyReports") or payload.get("annualReports") or []
    if not reports:
        from tradeagents.dataflows.errors import NoMarketDataError

        raise NoMarketDataError(ticker, ticker, f"no {title.lower()} returned")

    if curr_date:
        reports = [r for r in reports if r.get("fiscalDateEnding", "") <= curr_date]
        if not reports:
            from tradeagents.dataflows.errors import NoMarketDataError

            raise NoMarketDataError(
                ticker, ticker, f"no {title.lower()} on or before {curr_date}"
            )

    header = (
        f"# {title} for {ticker}\n"
        f"# Quarterly reports, most recent first; "
        f"periods end on the fiscalDateEnding shown\n\n"
    )
    # One line per report with its fields in a stable order, so successive
    # quarters diff cleanly.
    field_order = sorted(reports[0].keys() - {"fiscalDateEnding"})
    lines = [f"## {r['fiscalDateEnding']}" for r in reports]
    for report in reports:
        lines.append(f"\n### {report['fiscalDateEnding']}")
        lines.extend(f"{f}: {report.get(f, '')}" for f in field_order)
    return header + "\n".join(lines)


def get_balance_sheet(
    ticker: str, freq: str = "quarterly", curr_date: str | None = None
) -> str:
    return _statement("BALANCE_SHEET", ticker, curr_date, "Balance sheet")


def get_cashflow(
    ticker: str, freq: str = "quarterly", curr_date: str | None = None
) -> str:
    return _statement("CASH_FLOW", ticker, curr_date, "Cash flow")


def get_income_statement(
    ticker: str, freq: str = "quarterly", curr_date: str | None = None
) -> str:
    return _statement("INCOME_STATEMENT", ticker, curr_date, "Income statement")
