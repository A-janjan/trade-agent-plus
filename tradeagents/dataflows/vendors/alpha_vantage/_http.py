"""Alpha Vantage HTTP: one request helper, one error classification.

Every Alpha Vantage endpoint shares the same request shape — a query string
with ``function``, ``apikey``, and endpoint-specific params — and the same
two failure modes: a rate-limit notice or an invalid-key notice, both
delivered as a JSON body under ``Information`` or ``Note``. Classifying those
in one place means individual endpoints are three lines long and never have
to look at a response envelope.
"""

from __future__ import annotations

import json
import os

import requests

from tradeagents.dataflows.errors import (
    NoMarketDataError,
    VendorNotConfiguredError,
    VendorRateLimitError,
)

_BASE = "https://www.alphavantage.co/query"
_TIMEOUT = 30.0


class AlphaVantageNotConfigured(VendorNotConfiguredError):
    """Selected but no API key in the environment. Distinct type for clearer logs."""


def _api_key() -> str:
    key = os.environ.get("ALPHA_VANTAGE_API_KEY", "").strip()
    if not key:
        raise AlphaVantageNotConfigured(
            "ALPHA_VANTAGE_API_KEY is not set. Get a free key at "
            "https://www.alphavantage.co/support/#api-key."
        )
    return key


def _classify_notice(text: str) -> None:
    """Raise the right error for a rate-limit or invalid-key notice, else return.

    Rate-limit wording is checked first: those notices often mention the API
    key too ("your API key ... 25 requests per day"), so checking the key
    phrasing first would mislabel a throttle as a misconfiguration.
    """
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return  # a non-JSON body is data, not a notice
    notice = payload.get("Information") or payload.get("Note")
    if not notice:
        return
    low = notice.lower()
    if any(
        p in low
        for p in ("rate limit", "requests per day", "call frequency", "premium")
    ):
        raise VendorRateLimitError(f"Alpha Vantage rate limit: {notice}")
    if "api key" in low or "apikey" in low:
        raise AlphaVantageNotConfigured(f"Alpha Vantage API key invalid: {notice}")


def request(function: str, *, symbol: str, **params) -> str:
    """Call an Alpha Vantage endpoint; return its raw body as text.

    The key is redacted from any error the request raises, so a log or a
    traceback cannot leak it through a URL.
    """
    key = _api_key()
    query = {"function": function, "symbol": symbol, "apikey": key, **params}
    try:
        response = requests.get(_BASE, params=query, timeout=_TIMEOUT)
    except requests.RequestException as exc:
        # The exception text embeds the full URL including the key; scrub it
        # before re-raising so a caught log does not contain the credential.
        raise VendorRateLimitError(
            f"Alpha Vantage unreachable: {str(exc).replace(key, '***')}"
        ) from None
    text = response.text
    _classify_notice(text)
    if response.status_code >= 400:
        raise VendorRateLimitError(
            f"Alpha Vantage HTTP {response.status_code} for {function}"
        )
    if not text.strip():
        raise NoMarketDataError(symbol, symbol, f"empty response from {function}")
    return text
