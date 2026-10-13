from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from tradeagents.dataflows.vendors.polymarket import (
    _forward_looking,
    _parse_list,
)


@pytest.mark.unit
def test_parse_list_handles_json_string():
    assert _parse_list('["Yes","No"]') == ["Yes", "No"]


@pytest.mark.unit
def test_parse_list_handles_list():
    assert _parse_list(["Yes", "No"]) == ["Yes", "No"]


@pytest.mark.unit
def test_parse_list_returns_empty_on_garbage():
    assert _parse_list("not json") == []
    assert _parse_list(None) == []


@pytest.mark.unit
def test_forward_looking_rejects_closed():
    now = datetime.now(UTC)
    future = (now + timedelta(days=30)).isoformat()
    market = {
        "closed": True,
        "endDate": future,
        "outcomes": '["Yes","No"]',
        "outcomePrices": '["0.5","0.5"]',
    }
    assert not _forward_looking(market, now)


@pytest.mark.unit
def test_forward_looking_rejects_past_end_date():
    now = datetime.now(UTC)
    past = (now - timedelta(days=1)).isoformat()
    market = {
        "endDate": past,
        "outcomes": '["Yes","No"]',
        "outcomePrices": '["0.5","0.5"]',
    }
    assert not _forward_looking(market, now)


@pytest.mark.unit
def test_forward_looking_accepts_valid_open_market():
    now = datetime.now(UTC)
    future = (now + timedelta(days=30)).isoformat()
    market = {
        "endDate": future,
        "outcomes": '["Yes","No"]',
        "outcomePrices": '["0.5","0.5"]',
    }
    assert _forward_looking(market, now)


@pytest.mark.unit
def test_historical_run_withholds_odds():
    # A run dated before today gets a notice, not today's prices.
    from tradeagents.dataflows.vendors.polymarket import get_prediction_markets

    out = get_prediction_markets("Fed rate cut", "2020-01-01")
    assert "withheld" in out
