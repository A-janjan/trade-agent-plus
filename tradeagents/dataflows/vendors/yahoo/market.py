"""Yahoo Finance price and technical-indicator endpoints.

``get_stock_data`` returns raw OHLCV as CSV within a date range.
``get_stock_stats_indicators_window`` computes a technical indicator over a
trailing window using ``stockstats`` on the cached OHLCV frame.
"""

from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd
from dateutil.relativedelta import relativedelta
from stockstats import wrap

from tradeagents.dataflows.errors import NoMarketDataError, VendorError
from tradeagents.dataflows.symbols import normalize_symbol
from tradeagents.dataflows.vendors.yahoo.ohlcv import (
    _assert_ohlcv_not_stale,
    load_ohlcv,
    raise_for_empty,
    yf_retry,
)

logger = logging.getLogger(__name__)


# Descriptions surfaced alongside every indicator's values, so the analyst sees
# each indicator's intent without an external lookup.
INDICATOR_DESCRIPTIONS = {
    "close_50_sma": "50 SMA: Medium-term trend. Dynamic support/resistance; lags price.",
    "close_200_sma": "200 SMA: Long-term benchmark. Confirm trend; slow to react.",
    "close_10_ema": "10 EMA: Responsive short-term average. Capture quick momentum shifts.",
    "macd": "MACD: Momentum via differences of EMAs. Crossovers and divergence signal trend changes.",
    "macds": "MACD Signal: EMA smoothing of the MACD line. Use crossovers with MACD to trigger.",
    "macdh": "MACD Histogram: Gap between MACD and its signal. Visualize momentum strength.",
    "rsi": "RSI: Momentum 0–100. Watch 70/30 thresholds and divergence for reversals.",
    "boll": "Bollinger Middle: 20 SMA serving as the basis for Bollinger Bands.",
    "boll_ub": "Bollinger Upper Band: Typically 2σ above the middle. Overbought/breakout zones.",
    "boll_lb": "Bollinger Lower Band: Typically 2σ below the middle. Oversold zones.",
    "atr": "ATR: Averaged true range. Set stops and size positions against current volatility.",
    "vwma": "VWMA: Moving average weighted by volume. Confirm trends with volume.",
    "mfi": "MFI: Money Flow Index using price and volume. Overbought >80, oversold <20.",
}


def get_stock_data(symbol: str, start_date: str, end_date: str) -> str:
    """Return daily OHLCV as CSV for ``symbol`` within ``[start_date, end_date]``."""
    datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    canonical = normalize_symbol(symbol)
    end_inclusive = (end_dt + relativedelta(days=1)).strftime("%Y-%m-%d")
    data = yf_retry(
        lambda: __import__("yfinance")
        .Ticker(canonical)
        .history(
            start=start_date,
            end=end_inclusive,
        )
    )

    if data is None or data.empty:
        raise_for_empty(symbol, canonical, f"rows between {start_date} and {end_date}")

    if data.index.tz is not None:
        data.index = data.index.tz_localize(None)

    _assert_ohlcv_not_stale(data, end_date, symbol, canonical)

    for col in ("Open", "High", "Low", "Close", "Adj Close"):
        if col in data.columns:
            data[col] = data[col].round(2)

    label = canonical if canonical == symbol.upper() else f"{canonical} (from {symbol})"
    header = (
        f"# Stock data for {label} from {start_date} to {end_date}\n"
        f"# Total records: {len(data)}\n\n"
    )
    return header + data.to_csv()


def _get_stock_stats_bulk(
    symbol: str, indicator: str, curr_date: str
) -> dict[str, str]:
    """Compute ``indicator`` across every available date; return {date: value}."""
    data = load_ohlcv(symbol, curr_date)
    df = wrap(data)
    df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
    df[indicator]  # triggers stockstats to calculate the indicator

    result: dict[str, str] = {}
    for _, row in df.iterrows():
        value = row[indicator]
        result[row["Date"]] = "N/A" if pd.isna(value) else str(value)
    return result


def get_stock_stats_indicators_window(
    symbol: str,
    indicator: str,
    curr_date: str,
    look_back_days: int,
) -> str:
    """Indicator values for ``symbol`` over the trailing ``look_back_days``."""
    if indicator not in INDICATOR_DESCRIPTIONS:
        raise ValueError(
            f"Indicator {indicator} is not supported. Choose from: {list(INDICATOR_DESCRIPTIONS)}"
        )

    curr_dt = datetime.strptime(curr_date, "%Y-%m-%d")
    before = curr_dt - relativedelta(days=look_back_days)

    try:
        indicator_data = _get_stock_stats_bulk(symbol, indicator, curr_date)
    except VendorError:
        raise  # Unknown/delisted symbol — let the router emit the sentinel
    except Exception as e:
        raise NoMarketDataError(
            symbol,
            normalize_symbol(symbol),
            f"{indicator} unavailable: {e}",
        ) from e

    lines = []
    cursor = curr_dt
    while cursor >= before:
        date_str = cursor.strftime("%Y-%m-%d")
        value = indicator_data.get(date_str, "N/A: Not a trading day")
        lines.append(f"{date_str}: {value}")
        cursor = cursor - relativedelta(days=1)

    return (
        f"## {indicator} values from {before.strftime('%Y-%m-%d')} to {curr_date}:\n\n"
        + "\n".join(lines)
        + "\n\n"
        + INDICATOR_DESCRIPTIONS[indicator]
    )
