"""Alpha Vantage daily-adjusted OHLCV, filtered to the requested range.

Alpha Vantage returns the whole series (or the last 100 rows for ``compact``)
with ``TIME_SERIES_DAILY_ADJUSTED``; this module trims it. The trim is not
optional: the full series runs through today, and a historical run would
otherwise receive prices from after its analysis date.
"""

from __future__ import annotations

from datetime import datetime
from io import StringIO

import pandas as pd

from tradeagents.dataflows.errors import NoMarketDataError
from tradeagents.dataflows.vendors.alpha_vantage._http import request

# Below this many days between today and the requested start, ``compact``
# (last 100 rows) suffices and returns faster.
_COMPACT_WINDOW_DAYS = 100


def get_stock_data(symbol: str, start_date: str, end_date: str) -> str:
    """Daily adjusted OHLCV as CSV, trimmed to ``[start_date, end_date]``."""
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    days_back = (datetime.now() - start_dt).days
    outputsize = "compact" if days_back < _COMPACT_WINDOW_DAYS else "full"

    text = request(
        "TIME_SERIES_DAILY_ADJUSTED",
        symbol=symbol,
        outputsize=outputsize,
        datatype="csv",
    )

    # Alpha Vantage's CSV is well-formed; let a parse failure propagate as a
    # NoMarketDataError rather than serving an untrimmed series.
    try:
        df = pd.read_csv(StringIO(text))
    except Exception as exc:
        raise NoMarketDataError(symbol, symbol, f"unparseable CSV: {exc}") from exc

    if df.empty:
        raise NoMarketDataError(symbol, symbol, "no rows returned")
    date_col = df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col])
    df = df[(df[date_col] >= start_dt) & (df[date_col] <= end_dt)]
    if df.empty:
        raise NoMarketDataError(
            symbol, symbol, f"no rows between {start_date} and {end_date}"
        )

    header = (
        f"# Stock data for {symbol} from {start_date} to {end_date}\n"
        f"# Total records: {len(df)}\n\n"
    )
    return header + df.to_csv(index=False)
