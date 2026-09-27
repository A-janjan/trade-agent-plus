import pytest

from tradeagents.dataflows.symbols import normalize_symbol
from tradeagents.dataflows.vendors.yahoo import ohlcv


@pytest.mark.unit
def test_normalize_dates_handles_mixed_tz():
    import pandas as pd

    s = pd.Series(["2026-01-05 00:00:00+00:00", "2026-01-06 00:00:00+01:00", None])
    out = ohlcv._normalize_dates(s)
    assert out.iloc[0].date().isoformat() == "2026-01-05"
    # +01:00 shifts to the previous day in UTC; per-element normalization keeps
    # the local wall-clock date.
    assert out.iloc[1].date().isoformat() == "2026-01-06"
    assert out.iloc[2] is pd.NaT or str(out.iloc[2]) == "NaT"


@pytest.mark.unit
def test_assert_ohlcv_not_stale_rejects_old_frame():
    import pandas as pd

    df = pd.DataFrame({"Date": ["2020-01-02"], "Close": [100.0]})
    with pytest.raises(Exception):  # NoMarketDataError, kept loose on purpose
        ohlcv._assert_ohlcv_not_stale(df, "2026-09-01", "AAPL", "AAPL")


@pytest.mark.unit
def test_assert_ohlcv_not_stale_accepts_recent_frame():
    import pandas as pd

    df = pd.DataFrame({"Date": ["2026-08-28"], "Close": [100.0]})
    ohlcv._assert_ohlcv_not_stale(df, "2026-09-01", "AAPL", "AAPL")  # no raise


@pytest.mark.integration
def test_load_ohlcv_smoke():
    """Requires network + a real Yahoo symbol; run with `pytest -m integration`."""
    df = ohlcv.load_ohlcv("AAPL", "2026-09-01")
    assert not df.empty
    assert "Close" in df.columns
