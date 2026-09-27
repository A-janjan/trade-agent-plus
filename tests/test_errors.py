import pytest

from tradeagents.dataflows.errors import (
    NoMarketDataError,
    VendorError,
    VendorNotConfiguredError,
    VendorRateLimitError,
)


@pytest.mark.unit
def test_all_errors_derive_from_vendor_error():
    for cls in (NoMarketDataError, VendorRateLimitError, VendorNotConfiguredError):
        assert issubclass(cls, VendorError)


@pytest.mark.unit
def test_not_configured_is_also_value_error():
    assert issubclass(VendorNotConfiguredError, ValueError)


@pytest.mark.unit
def test_no_market_data_message_includes_canonical_when_different():
    err = NoMarketDataError("XAUUSD", "GC=F", "no rows")
    text = str(err)
    assert "XAUUSD" in text
    assert "GC=F" in text
    assert "no rows" in text


@pytest.mark.unit
def test_no_market_data_omits_canonical_when_same():
    err = NoMarketDataError("AAPL", "AAPL")
    assert "queried as" not in str(err)
