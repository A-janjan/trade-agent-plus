from __future__ import annotations

import pytest

from tradeagents.dataflows.vendors.sec_edgar import _SPANS, _as_of


@pytest.mark.unit
def test_as_of_picks_latest_filing_on_or_before_cutoff():
    # The same period was restated. A run dated between the two filings sees
    # the original figure; a run dated after the restatement sees the new one.
    facts = {
        "Assets": {
            "units": {
                "USD": [
                    {
                        "start": "2026-01-01",
                        "end": "2026-03-31",
                        "val": 100,
                        "filed": "2026-05-01",
                    },
                    {
                        "start": "2026-01-01",
                        "end": "2026-03-31",
                        "val": 110,
                        "filed": "2026-06-15",
                    },
                ]
            }
        },
    }
    values, unit = _as_of(facts, ("Assets",), "2026-05-15", _SPANS["quarterly"])
    assert values["2026-03-31"] == 100
    assert unit == "USD"

    values_after, _ = _as_of(facts, ("Assets",), "2026-06-20", _SPANS["quarterly"])
    assert values_after["2026-03-31"] == 110


@pytest.mark.unit
def test_as_of_ignores_facts_filed_after_cutoff():
    facts = {
        "Assets": {
            "units": {
                "USD": [
                    {
                        "start": "2026-01-01",
                        "end": "2026-03-31",
                        "val": 100,
                        "filed": "2026-05-01",
                    },
                ]
            }
        },
    }
    values, _ = _as_of(facts, ("Assets",), "2026-04-15", _SPANS["quarterly"])
    assert values == {}


@pytest.mark.unit
def test_as_of_falls_through_tags_in_order():
    facts = {
        "Revenues": {
            "units": {
                "USD": [
                    {
                        "start": "2026-01-01",
                        "end": "2026-03-31",
                        "val": 500,
                        "filed": "2026-05-01",
                    },
                ]
            }
        },
        "RevenueFromContractWithCustomerExcludingAssessedTax": {
            "units": {
                "USD": [
                    {
                        "start": "2026-04-01",
                        "end": "2026-06-30",
                        "val": 600,
                        "filed": "2026-08-01",
                    },
                ]
            }
        },
    }
    # First tag's periods are kept; second tag fills in periods it does not cover.
    values, _ = _as_of(
        facts,
        ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"),
        "2026-09-01",
        _SPANS["quarterly"],
    )
    assert values["2026-03-31"] == 500
    assert values["2026-06-30"] == 600


@pytest.mark.unit
def test_as_of_rejects_periods_outside_requested_span():
    # A half-year period does not satisfy a quarterly request.
    facts = {
        "Revenue": {
            "units": {
                "USD": [
                    {
                        "start": "2026-01-01",
                        "end": "2026-06-30",
                        "val": 1000,
                        "filed": "2026-07-30",
                    },
                ]
            }
        },
    }
    values, _ = _as_of(facts, ("Revenue",), "2026-09-01", _SPANS["quarterly"])
    assert values == {}


@pytest.mark.unit
def test_as_of_preserves_non_usd_unit():
    facts = {
        "EarningsPerShareDiluted": {
            "units": {
                "USD/shares": [
                    {
                        "start": "2026-01-01",
                        "end": "2026-03-31",
                        "val": 1.5,
                        "filed": "2026-05-01",
                    },
                ]
            }
        },
    }
    _, unit = _as_of(
        facts, ("EarningsPerShareDiluted",), "2026-06-01", _SPANS["quarterly"]
    )
    assert unit == "USD/shares"
