from __future__ import annotations

import pytest

from tradeagents.dataflows.vendors.fred import FredNotConfigured, _resolve, get_macro


@pytest.fixture(autouse=True)
def _clear_key(monkeypatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)


@pytest.mark.unit
def test_alias_resolution():
    assert _resolve("cpi") == "CPIAUCSL"
    assert _resolve("unemployment") == "UNRATE"
    assert _resolve("10y-treasury") == "DGS10"


@pytest.mark.unit
def test_raw_series_id_passes_through():
    assert _resolve("CPIAUCSL") == "CPIAUCSL"


@pytest.mark.unit
def test_descriptive_phrase_rejected():
    with pytest.raises(ValueError, match="not a known macro alias"):
        _resolve("bank of japan rate")


@pytest.mark.unit
def test_missing_key_raises_not_configured():
    with pytest.raises(FredNotConfigured):
        get_macro("cpi", "2026-09-01")


@pytest.mark.unit
def test_bad_alias_returns_guidance_not_raises():
    # A bad argument is user error; return guidance so it does not abort the run.
    out = get_macro("not a series id at all", "2026-09-01")
    assert out.startswith("FRED: ")
    assert "not a known macro alias" in out
