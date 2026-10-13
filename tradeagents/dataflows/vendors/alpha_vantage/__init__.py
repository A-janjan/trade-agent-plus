"""Alpha Vantage vendor: prices, indicators, fundamentals, news.

Requires ``ALPHA_VANTAGE_API_KEY``. Selected per method by listing it in the
configured vendor chain, e.g. ``data_vendors["core_stock_apis"] = "alpha_vantage"``
or ``"yfinance,alpha_vantage"`` for fallback.
"""

from tradeagents.dataflows.vendors.alpha_vantage.fundamentals import (
    get_balance_sheet,
    get_cashflow,
    get_fundamentals,
    get_income_statement,
)
from tradeagents.dataflows.vendors.alpha_vantage.indicators import get_indicators
from tradeagents.dataflows.vendors.alpha_vantage.news import get_global_news, get_news
from tradeagents.dataflows.vendors.alpha_vantage.prices import get_stock_data

__all__ = [
    "get_balance_sheet",
    "get_cashflow",
    "get_fundamentals",
    "get_global_news",
    "get_income_statement",
    "get_indicators",
    "get_news",
    "get_stock_data",
]
