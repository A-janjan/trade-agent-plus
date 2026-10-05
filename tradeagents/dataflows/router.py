"""Dispatch a data method to the configured vendor(s).

The configured value IS the chain: a call is served by the first configured
vendor that succeeds, and the router never silently falls back to a vendor the
user did not choose. Fallback is explicit — to fall back, list several vendors
in order, e.g. ``data_vendors["core_stock_apis"] = "yfinance,alpha_vantage"``.

Vendor failures are handled by behavior, not by vendor name:

    VendorNotConfiguredError  -> vendor has no key/config; try next
    VendorRateLimitError      -> vendor throttled/unreachable; try next
    NoMarketDataError         -> vendor has no usable rows; try next
    Any other exception       -> logged, try next (a broken primary must be
                                 visible in the logs, not hidden behind a
                                 fallback's verdict)

After exhausting the chain, one explicit sentinel is returned: a single
"unavailable" signal the agent can report honestly, instead of a
vendor-specific empty string it might fabricate a value around.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from tradeagents.dataflows.config import get_config
from tradeagents.dataflows.errors import (
    NoMarketDataError,
    VendorNotConfiguredError,
    VendorRateLimitError,
)
from tradeagents.dataflows.vendors.yahoo.fundamentals import (
    get_balance_sheet as get_yfinance_balance_sheet,
    get_cashflow as get_yfinance_cashflow,
    get_fundamentals as get_yfinance_fundamentals,
    get_income_statement as get_yfinance_income_statement,
)
from tradeagents.dataflows.vendors.yahoo.market import (
    get_stock_data as get_yfinance_stock_data,
    get_stock_stats_indicators_window as get_yfinance_indicators,
)
from tradeagents.dataflows.vendors.yahoo.news import (
    get_global_news as get_yfinance_global_news,
    get_news as get_yfinance_news,
)

logger = logging.getLogger(__name__)


# Category -> tool methods. Categories group tools that share a vendor setting
# (e.g. all technical indicators can come from the same vendor).
TOOLS_CATEGORIES = {
    "core_stock_apis": {
        "description": "OHLCV stock price data",
        "tools": ["get_stock_data"],
    },
    "technical_indicators": {
        "description": "Technical analysis indicators",
        "tools": ["get_indicators"],
    },
    "fundamental_data": {
        "description": "Company fundamentals",
        "tools": [
            "get_fundamentals",
            "get_balance_sheet",
            "get_cashflow",
            "get_income_statement",
        ],
    },
    "news_data": {
        "description": "News and macro",
        "tools": ["get_news", "get_global_news"],
    },
}


# Method -> {vendor name: callable}. Adding a vendor here is all that is needed
# to make it selectable for a method.
VENDOR_METHODS: dict[str, dict[str, Callable[..., Any]]] = {
    "get_stock_data": {"yfinance": get_yfinance_stock_data},
    "get_indicators": {"yfinance": get_yfinance_indicators},
    "get_fundamentals": {"yfinance": get_yfinance_fundamentals},
    "get_balance_sheet": {"yfinance": get_yfinance_balance_sheet},
    "get_cashflow": {"yfinance": get_yfinance_cashflow},
    "get_income_statement": {"yfinance": get_yfinance_income_statement},
    "get_news": {"yfinance": get_yfinance_news},
    "get_global_news": {"yfinance": get_yfinance_global_news},
}


def get_category_for_method(method: str) -> str:
    for category, info in TOOLS_CATEGORIES.items():
        if method in info["tools"]:
            return category
    raise ValueError(f"Method {method!r} not found in any category")


def get_vendor(category: str, method: str | None = None) -> str:
    """Configured vendor(s) for a category or a specific method.

    Tool-level configuration takes precedence over category-level.
    """
    config = get_config()
    if method:
        tool_vendors = config.get("tool_vendors", {})
        if method in tool_vendors:
            return tool_vendors[method]
    return config.get("data_vendors", {}).get(category, "")


def _configured_chain(vendor_config: str, method: str) -> list[str]:
    """Parse the configured vendor string into an ordered chain of implementations.

    Raises when a configured vendor does not serve the method — that is a
    misconfiguration, and silently substituting another vendor would defeat the
    "explicit chain" rule.
    """
    available = VENDOR_METHODS[method]
    requested = [v.strip() for v in (vendor_config or "").split(",") if v.strip()]

    if not requested:
        raise ValueError(
            f"No vendor configured for {method!r}. Set data_vendors or tool_vendors."
        )

    unknown = [v for v in requested if v not in available]
    if unknown:
        raise ValueError(
            f"Configured vendor(s) {unknown} not available for {method!r}. "
            f"Available: {list(available)}."
        )
    return requested


def route_to_vendor(method: str, *args, **kwargs):
    """Route a method call to the configured vendor chain with explicit fallback."""
    if method not in VENDOR_METHODS:
        raise ValueError(f"Method {method!r} not supported")

    category = get_category_for_method(method)
    vendor_config = get_vendor(category, method)
    chain = _configured_chain(vendor_config, method)

    last_no_data: NoMarketDataError | None = None
    last_unavailable: VendorRateLimitError | None = None
    first_error: Exception | None = None

    for vendor in chain:
        impl = VENDOR_METHODS[method][vendor]
        try:
            return impl(*args, **kwargs)
        except VendorRateLimitError as e:
            logger.warning(
                "Vendor %r unavailable for %s: %s; trying next.", vendor, method, e
            )
            last_unavailable = e
        except VendorNotConfiguredError as e:
            logger.warning(
                "Vendor %r not configured for %s; trying next.", vendor, method
            )
            if first_error is None:
                first_error = e
        except NoMarketDataError as e:
            last_no_data = e
        except (
            Exception
        ) as e:  # noqa: BLE001 — one vendor's failure must not abort the call
            logger.warning("Vendor %r failed for %s: %s", vendor, method, e)
            if first_error is None:
                first_error = e

    # Any vendor reporting "no data" means the symbol is genuinely unavailable.
    if last_no_data is not None:
        if first_error is not None:
            logger.warning(
                "Returning NO_DATA for %s, but a vendor errored earlier: %s",
                method,
                first_error,
            )
        sym = last_no_data.symbol
        canonical = last_no_data.canonical
        resolved = "" if canonical == sym else f" (resolved to {canonical!r})"
        reason = f" ({last_no_data.detail})" if last_no_data.detail else ""
        return (
            f"NO_DATA_AVAILABLE: no usable market data for {sym!r}{resolved} from any "
            f"configured vendor{reason}. The symbol may be invalid, delisted, not "
            f"covered, or the vendor returned stale data. Do not estimate or "
            f"fabricate values — report that data is unavailable."
        )

    if last_unavailable is not None:
        return (
            f"DATA_UNAVAILABLE: no configured vendor could serve {method} right now "
            f"({last_unavailable}). This says nothing about the instrument."
        )

    if first_error is not None:
        raise first_error

    raise RuntimeError(f"No available vendor for {method!r}")
