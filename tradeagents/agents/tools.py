"""LangChain tool wrappers around the vendor router.

Each tool takes the run's ``trade_date`` from graph state (via ``InjectedState``)
and never serves data past it, whatever date the model asks for. This is the
single point where the LLM's view of the world is clamped to the analysis date.
"""

from __future__ import annotations

from typing import Annotated

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from tradeagents.dataflows.date_window import as_of
from tradeagents.dataflows.router import route_to_vendor


@tool
def get_stock_data(
    symbol: Annotated[str, "Ticker symbol, e.g. AAPL, NVDA, BTC-USD"],
    start_date: Annotated[str, "Start date YYYY-MM-DD"],
    end_date: Annotated[str, "End date YYYY-MM-DD"],
    trade_date: Annotated[str, InjectedState("trade_date")] = "",
) -> str:
    """Daily OHLCV price history for a ticker, as CSV.

    Use this first to fetch price data before requesting indicators.
    """
    start_date = as_of(start_date, trade_date) or start_date
    end_date = as_of(end_date, trade_date) or end_date
    return route_to_vendor("get_stock_data", symbol, start_date, end_date)


@tool
def get_indicators(
    symbol: Annotated[str, "Ticker symbol"],
    indicator: Annotated[str, "One indicator name, e.g. 'rsi', 'macd', 'close_50_sma'"],
    curr_date: Annotated[str, "Analysis date YYYY-MM-DD"],
    look_back_days: Annotated[int, "Trailing window in days"] = 30,
    trade_date: Annotated[str, InjectedState("trade_date")] = "",
) -> str:
    """Trailing values of one technical indicator, with a short description.

    Supported: close_10_ema, close_50_sma, close_200_sma, macd, macds, macdh,
    rsi, boll, boll_ub, boll_lb, atr, vwma, mfi. Call once per indicator.
    """
    curr_date = as_of(curr_date, trade_date) or curr_date
    return route_to_vendor(
        "get_indicators", symbol, indicator, curr_date, look_back_days
    )
