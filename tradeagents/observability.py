"""Optional Langfuse tracing.

Langfuse attaches to LangGraph through the LangChain callback system, so the
integration is: build a callback handler when credentials are present, hand it
to the graph config, and the whole run — every node, LLM call, and tool call —
shows up as a nested trace.

Nothing here is required. Without ``LANGFUSE_PUBLIC_KEY`` and
``LANGFUSE_SECRET_KEY`` in the environment, ``build_callbacks`` returns an empty
list and the pipeline runs exactly as it did before. The ``langfuse`` package
itself is an optional extra (``pip install tradeagents[observability]``), so the
core install stays lean.

The Langfuse SDK's import path changed between major versions; ``_handler_class``
resolves whichever one is installed rather than pinning a version.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_REQUIRED_ENV = ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY")


def langfuse_enabled(config: dict | None = None) -> bool:
    """Whether tracing should be wired up.

    ``config["langfuse"]`` is ``"auto"`` (default, trace when both credentials
    are present), ``"on"`` (require credentials; raise when absent, because a
    silent skip would be a lie), or ``"off"`` (never trace).
    """
    mode = ((config or {}).get("langfuse") or "auto").lower()
    if mode == "off":
        return False
    missing = [v for v in _REQUIRED_ENV if not os.environ.get(v)]
    if mode == "on":
        if missing:
            raise ValueError(
                f"langfuse='on' but {missing} not set. Set both, or use "
                f"langfuse='auto' to skip tracing when credentials are absent."
            )
        return True
    return not missing


def _handler_class():
    """Resolve Langfuse's LangChain callback handler across SDK versions.

    SDK v3+ exposes the handler at ``langfuse.langchain``; v2 kept it at
    ``langfuse.callback``. Returns None when langfuse is not installed or the
    handler module is unavailable in the installed version.
    """
    # Try importing the top-level package first so we can distinguish a
    # "package missing" situation (no warning needed) from a "module missing
    # inside an installed package" situation.
    try:
        import langfuse  # noqa: F401
    except ImportError:
        return None

    # Each candidate is tried in order; the first that resolves wins.
    candidates = [
        "langfuse.langchain.CallbackHandler",  # SDK v3+
        "langfuse.callback.CallbackHandler",  # SDK v2
        "langfuse.CallbackHandler",  # earlier releases
    ]
    import importlib

    for dotted in candidates:
        try:
            module_path, attr = dotted.rsplit(".", 1)
            module = importlib.import_module(module_path)
            return getattr(module, attr)
        except (ImportError, AttributeError):
            continue
    return None


def build_callbacks(config: dict | None = None) -> list[Any]:
    """Return the callback handlers to pass to the graph, or ``[]``.

    A missing ``langfuse`` package is logged once and treated as disabled — the
    user may have credentials set from a previous install and simply not want
    the extra dependency today.
    """
    if not langfuse_enabled(config):
        return []
    handler_cls = _handler_class()
    if handler_cls is None:
        logger.warning(
            "Langfuse credentials are set but the 'langfuse' package is not "
            "installed; tracing is disabled. Install with "
            "`pip install tradeagents[observability]`."
        )
        return []
    return [handler_cls()]


def trace_metadata(
    ticker: str,
    trade_date: str,
    *,
    asset_type: str = "stock",
    session_id: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Run metadata Langfuse reads to name, group, and tag a trace.

    Keys are the ones the LangChain integration documents: ``langfuse_session_id``
    groups runs (use one per ticker to see its history), ``langfuse_tags``
    filter the dashboard, and ``run_name`` sets the trace's display name. The
    remaining keys are plain metadata, visible on the trace but not indexed.
    """
    meta: dict[str, Any] = {
        "run_name": f"tradeagents · {ticker} · {trade_date}",
        "langfuse_tags": tags or ["tradeagents", asset_type],
        "ticker": ticker,
        "trade_date": trade_date,
        "asset_type": asset_type,
    }
    if session_id:
        meta["langfuse_session_id"] = session_id
    return meta


def flush() -> None:
    """Flush pending events to Langfuse.

    Call at the end of a short-lived process (a CLI run, a script) — the SDK
    batches events and a process that exits before the batch drains loses them.
    Safe to call when tracing is disabled or not installed.
    """
    handler_cls = _handler_class()
    if handler_cls is None:
        return
    try:
        from langfuse import get_client

        get_client().flush()
    except (ImportError, AttributeError):
        # Older SDKs expose flush on the Langfuse class instead of the client.
        try:
            from langfuse import Langfuse

            Langfuse().flush()
        except Exception as exc:  # noqa: BLE001 — flushing must never fail a run
            logger.debug("Langfuse flush failed: %s", exc)
