import pytest

from tradeagents.dataflows.symbols import (
    crypto_base,
    normalize_symbol,
    safe_ticker_component,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("AAPL", "AAPL"),
        ("aapl", "AAPL"),
        ("XAUUSD", "GC=F"),
        ("XAUUSD+", "GC=F"),
        ("SPX500", "^GSPC"),
        ("US500", "^GSPC"),
        ("EURUSD", "EURUSD=X"),
        ("BTCUSD", "BTC-USD"),
        ("BTC-USD", "BTC-USD"),
        ("BTCUSDT", "BTC-USD"),
        ("eth-usd", "ETH-USD"),
        ("700.HK", "0700.HK"),
        ("09992.HK", "9992.HK"),
        ("600519.SH", "600519.SS"),
        ("GC=F", "GC=F"),
        ("^GSPC", "^GSPC"),
    ],
)
def test_normalize_symbol(raw, expected):
    assert normalize_symbol(raw) == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("BTC-USD", "BTC"),
        ("BTCUSD", "BTC"),
        ("BTC-USDT", "BTC"),
        ("AAPL", None),
        ("EURUSD", None),
        ("", None),
    ],
)
def test_crypto_base(raw, expected):
    assert crypto_base(raw) == expected


@pytest.mark.unit
def test_safe_ticker_accepts_normal():
    assert safe_ticker_component("AAPL") == "AAPL"
    assert safe_ticker_component("BTC-USD") == "BTC-USD"
    assert safe_ticker_component("^GSPC") == "^GSPC"
    assert safe_ticker_component("GC=F") == "GC=F"


@pytest.mark.unit
@pytest.mark.parametrize(
    "bad",
    [
        "",
        "..",
        "...",
        "../../etc/passwd",
        "AAPL/../etc",
        "a" * 33,
        "NVDA;rm",
    ],
)
def test_safe_ticker_rejects(bad):
    with pytest.raises(ValueError):
        safe_ticker_component(bad)
