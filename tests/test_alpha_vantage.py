from __future__ import annotations

import pytest

from tradeagents.dataflows.errors import VendorRateLimitError
from tradeagents.dataflows.vendors.alpha_vantage._http import (
    AlphaVantageNotConfigured,
    _classify_notice,
)


@pytest.fixture(autouse=True)
def _clear_key(monkeypatch):
    monkeypatch.delenv("ALPHA_VANTAGE_API_KEY", raising=False)


@pytest.mark.unit
def test_missing_key_raises_not_configured():
    from tradeagents.dataflows.vendors.alpha_vantage._http import request

    with pytest.raises(AlphaVantageNotConfigured):
        request("OVERVIEW", symbol="IBM")


@pytest.mark.unit
def test_notice_rate_limit_classified():
    with pytest.raises(VendorRateLimitError):
        _classify_notice(
            '{"Information": "you have reached the rate limit of 25 requests per day"}'
        )


@pytest.mark.unit
def test_notice_invalid_key_classified():
    with pytest.raises(AlphaVantageNotConfigured):
        _classify_notice('{"Information": "the API key provided is invalid"}')


@pytest.mark.unit
def test_rate_limit_wording_checked_before_key_wording():
    # Rate-limit notices often mention "API key" too; the check must not
    # mislabel them as a configuration problem.
    with pytest.raises(VendorRateLimitError):
        _classify_notice('{"Note": "your API key ... 25 requests per day"}')


@pytest.mark.unit
def test_data_body_passes_through():
    # A non-JSON body is data, not a notice.
    _classify_notice("timestamp,open,high\n2026-01-01,100,101\n")


@pytest.mark.unit
def test_indicators_rejects_unknown_name():
    from tradeagents.dataflows.vendors.alpha_vantage.indicators import get_indicators

    with pytest.raises(Exception, match="does not serve"):
        get_indicators("IBM", "not_an_indicator", "2026-09-01", 30)
