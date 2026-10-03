import pytest

from tradeagents.dataflows import router
from tradeagents.dataflows.config import reset_config, set_config
from tradeagents.dataflows.errors import (
    NoMarketDataError,
    VendorRateLimitError,
)


@pytest.fixture
def restore_config():
    yield
    reset_config()


@pytest.mark.unit
def test_router_refuses_unknown_method():
    with pytest.raises(ValueError, match="not supported"):
        router.route_to_vendor("no_such_method")


@pytest.mark.unit
def test_router_raises_when_no_vendor_configured():
    set_config({"tool_vendors": {"get_stock_data": ""}})
    with pytest.raises(ValueError, match="No vendor configured"):
        router.route_to_vendor("get_stock_data", "AAPL", "2026-01-01", "2026-02-01")


@pytest.mark.unit
def test_router_rejects_unknown_vendor(restore_config):
    set_config({"tool_vendors": {"get_stock_data": "no_such_vendor"}})
    with pytest.raises(ValueError, match="not available"):
        router.route_to_vendor("get_stock_data", "AAPL", "2026-01-01", "2026-02-01")


@pytest.mark.unit
def test_router_sentinel_on_no_market_data(monkeypatch, restore_config):
    def boom(*_a, **_kw):
        raise NoMarketDataError("ZZZZ", "ZZZZ", "empty")

    monkeypatch.setitem(router.VENDOR_METHODS["get_stock_data"], "yfinance", boom)
    out = router.route_to_vendor("get_stock_data", "ZZZZ", "2026-01-01", "2026-02-01")
    assert out.startswith("NO_DATA_AVAILABLE")
    assert "ZZZZ" in out


@pytest.mark.unit
def test_router_sentinel_on_rate_limit(monkeypatch, restore_config):
    def boom(*_a, **_kw):
        raise VendorRateLimitError("throttled")

    monkeypatch.setitem(router.VENDOR_METHODS["get_stock_data"], "yfinance", boom)
    out = router.route_to_vendor("get_stock_data", "AAPL", "2026-01-01", "2026-02-01")
    assert out.startswith("DATA_UNAVAILABLE")


@pytest.mark.unit
def test_router_raises_first_error_when_no_vendor_served(monkeypatch, restore_config):
    def boom(*_a, **_kw):
        raise RuntimeError("net down")

    monkeypatch.setitem(router.VENDOR_METHODS["get_stock_data"], "yfinance", boom)
    with pytest.raises(RuntimeError, match="net down"):
        router.route_to_vendor("get_stock_data", "AAPL", "2026-01-01", "2026-02-01")
