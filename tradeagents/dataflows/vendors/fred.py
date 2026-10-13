"""FRED macro series.

The St. Louis Fed's FRED serves policy rates, Treasury yields, inflation,
labor, and growth. A free key goes in ``FRED_API_KEY``.

Point-in-time matters here more than anywhere else: economic series are
revised. FRED reports every observation with the date it was published, so a
run dated in the past can ask for the vintage that was current then — not
today's revised figure. Without this, a backtest would read GDP and CPI as
they are known now, which is a look-ahead leak.

The current live run pins ``realtime_start=realtime_end=curr_date``, clamped
to FRED's own "today". A past run gets the vintage it would have seen.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta

import requests

from tradeagents.dataflows.errors import VendorNotConfiguredError
from tradeagents.dataflows.vendors.alpha_vantage._http import _TIMEOUT  # reuse

logger = logging.getLogger(__name__)

_BASE = "https://api.stlouisfed.org/fred"

# Friendly names -> FRED series IDs. Anything not listed is used verbatim as a
# series ID, so a user is never limited to this table.
_ALIASES = {
    "fed_funds_rate": "FEDFUNDS",
    "fed_funds": "FEDFUNDS",
    "federal_funds": "FEDFUNDS",
    "2y_treasury": "DGS2",
    "10y_treasury": "DGS10",
    "30y_treasury": "DGS30",
    "yield_curve": "T10Y2Y",
    "10y_2y_spread": "T10Y2Y",
    "cpi": "CPIAUCSL",
    "core_cpi": "CPILFESL",
    "pce": "PCEPI",
    "core_pce": "PCEPILFE",
    "inflation_expectations": "T10YIE",
    "gdp": "GDP",
    "real_gdp": "GDPC1",
    "industrial_production": "INDPRO",
    "unemployment": "UNRATE",
    "unemployment_rate": "UNRATE",
    "nonfarm_payrolls": "PAYEMS",
    "payrolls": "PAYEMS",
    "initial_claims": "ICSA",
    "m2": "M2SL",
    "vix": "VIXCLS",
    "dollar_index": "DTWEXBGS",
    "consumer_sentiment": "UMCSENT",
    "housing_starts": "HOUST",
    "retail_sales": "RSAFS",
}

_DEFAULT_LOOKBACK_DAYS = 365
_MAX_ROWS = 40


class FredNotConfigured(VendorNotConfiguredError):
    """Selected but no API key. Distinct type for clearer logs."""


def _key() -> str:
    key = os.environ.get("FRED_API_KEY", "").strip()
    if not key:
        raise FredNotConfigured(
            "FRED_API_KEY is not set. Get a free key at "
            "https://fred.stlouisfed.org/docs/api/api_key.html."
        )
    return key


def _resolve(indicator: str) -> str:
    """Map an alias to a FRED series ID, or pass a raw ID through.

    Rejects descriptive phrases a model may pass (``"bank of japan rate"``)
    before they hit the API, since FRED would return a confusing 400.
    """
    key = indicator.strip().lower().replace(" ", "_").replace("-", "_")
    if key in _ALIASES:
        return _ALIASES[key]
    candidate = indicator.strip().upper()
    if not candidate or len(candidate) > 30 or any(c.isspace() for c in candidate):
        raise ValueError(
            f"{indicator!r} is not a known macro alias or a plausible FRED series ID. "
            f"Use an alias like 'cpi', 'unemployment', '10y_treasury', or a raw ID "
            f"like 'CPIAUCSL'."
        )
    return candidate


def _fred_today() -> str:
    """FRED's own calendar date, US Central.

    FRED rejects a realtime date in its future with a 400. A live run's
    ``curr_date`` comes from the caller's local clock, which can already be
    tomorrow in Chicago; clamping to FRED's today keeps a live request valid.
    """
    # A fixed offset is fine here — the pin only needs to be within a day.
    return (datetime.utcnow() - timedelta(hours=6)).strftime("%Y-%m-%d")


def get_macro(indicator: str, curr_date: str, look_back_days: int | None = None) -> str:
    """A macro series as a markdown report, at the vintage known by ``curr_date``.

    ``look_back_days`` bounds the observation window; the vintage pin is the
    more important bound, and it is set by ``curr_date`` so a historical run
    reads the values that were published by then, not today's revisions.
    """
    if look_back_days is None:
        look_back_days = _DEFAULT_LOOKBACK_DAYS

    try:
        series_id = _resolve(indicator)
    except ValueError as exc:
        # A bad argument is a user error, not a vendor error — return guidance
        # rather than raising, so a bad argument does not abort the run.
        return f"FRED: {exc}"

    end_dt = datetime.strptime(curr_date, "%Y-%m-%d")
    start_date = (end_dt - timedelta(days=look_back_days)).strftime("%Y-%m-%d")

    # The vintage pin. Both realtime bounds set to the same day asks FRED for
    # the values known as of that day — not today's revisions.
    pin = min(curr_date, _fred_today())
    realtime = {"realtime_start": pin, "realtime_end": pin}

    try:
        meta = _request("series", {"series_id": series_id, **realtime})
        observations = _request(
            "series/observations",
            {
                "series_id": series_id,
                "observation_start": start_date,
                "observation_end": curr_date,
                "sort_order": "asc",
                **realtime,
            },
        )
    except requests.RequestException as exc:
        return f"FRED is unreachable ({type(exc).__name__}); the macro series could not be retrieved."

    series_list = meta.get("seriess") or []
    if not series_list:
        return (
            f"FRED series {series_id!r} not found. Pass a known alias "
            f"(e.g. 'cpi', 'unemployment') or a valid FRED series ID."
        )
    info = series_list[0]

    # FRED encodes a missing observation as ".". Drop those before the table.
    points = [
        (o["date"], o["value"])
        for o in observations.get("observations", [])
        if o.get("value") not in (".", None, "")
    ]
    header = (
        f"## FRED: {info.get('title', series_id)} ({series_id})\n"
        f"- Units: {info.get('units_short') or info.get('units', '')}\n"
        f"- Frequency: {info.get('frequency', '')}\n"
        f"- Window: {start_date} to {curr_date} at vintage {pin}\n"
    )
    if not points:
        return header + (
            f"\nNo observations in this window at the {pin} vintage. The series "
            f"may report less frequently than the window, or have no vintage "
            f"published by then."
        )

    first_date, first_val = points[0]
    last_date, last_val = points[-1]
    try:
        delta = float(last_val) - float(first_val)
        base = float(first_val)
        pct = f" ({delta / base * 100:+.2f}%)" if base else ""
        summary = (
            f"\n**Latest:** {last_val} ({last_date}) | "
            f"**Change over window:** {delta:+.2f}{pct} from {first_val} ({first_date})\n"
        )
    except ValueError:
        summary = f"\n**Latest:** {last_val} ({last_date})\n"

    shown = points[-_MAX_ROWS:]
    note = (
        f"\n_(showing the most recent {_MAX_ROWS} of {len(points)} observations)_\n"
        if len(points) > _MAX_ROWS
        else ""
    )
    table = (
        "\n| Date | Value |\n| --- | --- |\n"
        + "\n".join(f"| {d} | {v} |" for d, v in shown)
        + "\n"
    )
    return header + summary + note + table


def _request(path: str, params: dict) -> dict:
    """Call a FRED endpoint, turning a 400 error body into a clear message."""
    key = _key()
    response = requests.get(
        f"{_BASE}/{path}",
        params={**params, "api_key": key, "file_type": "json"},
        timeout=_TIMEOUT,
    )
    if response.status_code == 400:
        try:
            message = response.json().get("error_message", response.text)
        except ValueError:
            message = response.text
        raise ValueError(f"FRED request failed: {message}")
    response.raise_for_status()
    return response.json()
