"""Alpha Vantage technical indicators.

Only the endpoints this system exposes are implemented; the mapping from a
stockstats-style name (``rsi``, ``macd``) to an Alpha Vantage endpoint and
parameters is a table. Adding a new indicator is a table entry.
"""

from __future__ import annotations

import io
from datetime import datetime

import pandas as pd

from tradeagents.dataflows.errors import NoMarketDataError
from tradeagents.dataflows.vendors.alpha_vantage._http import request

# name -> (endpoint, extra params, CSV column to read)
_INDICATORS: dict[str, tuple[str, dict, str]] = {
    "rsi": ("RSI", {"time_period": "14", "series_type": "close"}, "RSI"),
    "macd": ("MACD", {"series_type": "close"}, "MACD"),
    "macds": ("MACD", {"series_type": "close"}, "MACD_Signal"),
    "macdh": ("MACD", {"series_type": "close"}, "MACD_Hist"),
    "close_10_ema": ("EMA", {"time_period": "10", "series_type": "close"}, "EMA"),
    "close_50_sma": ("SMA", {"time_period": "50", "series_type": "close"}, "SMA"),
    "close_200_sma": ("SMA", {"time_period": "200", "series_type": "close"}, "SMA"),
    "boll": (
        "BBANDS",
        {"time_period": "20", "series_type": "close"},
        "Real Middle Band",
    ),
    "boll_ub": (
        "BBANDS",
        {"time_period": "20", "series_type": "close"},
        "Real Upper Band",
    ),
    "boll_lb": (
        "BBANDS",
        {"time_period": "20", "series_type": "close"},
        "Real Lower Band",
    ),
    "atr": ("ATR", {"time_period": "14"}, "ATR"),
}


def supported_indicators() -> list[str]:
    return sorted(_INDICATORS)


def get_indicators(
    symbol: str, indicator: str, curr_date: str, look_back_days: int
) -> str:
    """A trailing window of one indicator's values, as a date-value table."""
    key = indicator.strip().lower()
    if key not in _INDICATORS:
        raise NoMarketDataError(
            symbol,
            symbol,
            f"Alpha Vantage does not serve {indicator!r}; serves {supported_indicators()}",
        )
    endpoint, params, column = _INDICATORS[key]

    text = request(endpoint, symbol=symbol, datatype="csv", **params)
    try:
        df = pd.read_csv(io.StringIO(text))
    except Exception as exc:
        raise NoMarketDataError(symbol, symbol, f"unparseable CSV: {exc}") from exc
    if df.empty or "time" not in df.columns:
        raise NoMarketDataError(symbol, symbol, "missing 'time' column")

    curr_dt = datetime.strptime(curr_date, "%Y-%m-%d")
    df["time"] = pd.to_datetime(df["time"])
    cutoff = curr_dt - pd.Timedelta(days=look_back_days)
    df = df[(df["time"] >= cutoff) & (df["time"] <= curr_dt)].sort_values("time")
    if df.empty:
        raise NoMarketDataError(symbol, symbol, "no rows in the requested window")

    rows = "\n".join(
        f"{row['time'].strftime('%Y-%m-%d')}: {row[column]}" for _, row in df.iterrows()
    )
    return (
        f"## {key} values from {cutoff.strftime('%Y-%m-%d')} to {curr_date}:\n\n{rows}"
    )
