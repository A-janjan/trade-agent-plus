"""Prompt context shared across agents: language, instrument identity."""

from __future__ import annotations

import functools
import logging

import yfinance as yf
from langchain_core.messages import HumanMessage, RemoveMessage

from tradeagents.dataflows.config import get_config
from tradeagents.dataflows.date_window import get_current_date
from tradeagents.dataflows.symbols import normalize_symbol

logger = logging.getLogger(__name__)


def get_language_instruction() -> str:
    """Instruction to write in the configured language, or '' for English.

    Applied to every agent whose output reaches the saved report, so a
    non-English run produces a fully localized report rather than a mix.
    """
    lang = get_config().get("output_language", "English")
    if (lang or "").strip().lower() == "english":
        return ""
    return f"\n\nWrite your entire response in {lang}."


@functools.lru_cache(maxsize=256)
def _resolve_identity(ticker: str) -> dict[str, str]:
    """Best-effort company profile via yfinance; empty dict on any failure.

    Exists to stop the pipeline from hallucinating a *different* company when
    a chart pattern suggests a different industry than the real one. Fail-open
    by design: a lookup failure means the analyst gets ticker-only context, not
    a run that aborts before analysis starts. Cached per-process.
    """
    canonical = normalize_symbol(ticker)
    try:
        info = yf.Ticker(canonical).info or {}
    except Exception as exc:  # noqa: BLE001 — fail open, never block the run
        logger.debug("Identity lookup failed for %s: %s", ticker, exc)
        return {}

    out: dict[str, str] = {}
    for src, dst in (
        ("longName", "name"),
        ("shortName", "name"),
        ("sector", "sector"),
        ("industry", "industry"),
        ("exchange", "exchange"),
    ):
        value = info.get(src)
        if value and dst not in out:
            out[dst] = str(value)
    return out


def build_instrument_context(
    ticker: str, asset_type: str = "stock", curr_date: str | None = None
) -> str:
    """Describe the instrument for every agent's system prompt.

    Includes the resolved company name and business classification when
    available, so agents anchor to the real company. A profile carries no
    historical vintage — it describes the company today — so a run dated in
    the past is told so explicitly.
    """
    is_crypto = asset_type == "crypto"
    label = "asset" if is_crypto else "instrument"
    parts = [
        f"The {label} to analyze is `{ticker}`. Use this exact ticker in every "
        f"tool call and report."
    ]

    identity = _resolve_identity(ticker)
    details: list[str] = []
    if identity.get("name"):
        details.append(f"{'Name' if is_crypto else 'Company'}: {identity['name']}")
    if identity.get("sector") and identity.get("industry"):
        details.append(
            f"Business classification: {identity['sector']} / {identity['industry']}"
        )
    elif identity.get("sector"):
        details.append(f"Sector: {identity['sector']}")
    if identity.get("exchange"):
        details.append(f"Exchange: {identity['exchange']}")

    if details:
        parts.append("Resolved identity: " + "; ".join(details) + ".")
        today = get_current_date()
        if curr_date and curr_date < today:
            parts.append(
                f"This identity reflects how the vendor describes the instrument "
                f"today, not necessarily on {curr_date}."
            )

    if is_crypto:
        parts.append(
            "Treat it as a crypto asset, not a company, and do not expect "
            "company fundamentals."
        )
    return " ".join(parts)


def report_or_absent(text: str, source: str) -> str:
    """An analyst's report, or a marker saying it was never produced.

    A report is empty when its analyst was not selected or returned nothing.
    Interpolating that into a labelled section presents an absence as a blank
    finding, and the reading agent fills it in from nothing — the same way an
    empty opponent argument invites an invented rebuttal.
    """
    text = (text or "").strip()
    if text:
        return text
    return (
        f"(No {source} report in this run: it is not available, not an empty finding.)"
    )


def create_msg_delete():
    """Factory for a node that clears messages and re-anchors the next analyst.

    The placeholder must not be a bare ``"Continue"``: some OpenAI-compatible
    providers interpret that literally as the user task. Anchoring it to the
    instrument context and date keeps the next analyst on-task.
    """

    def delete_messages(state):
        removals = [RemoveMessage(id=m.id) for m in state["messages"]]
        instrument_context = state.get("instrument_context", "")
        trade_date = state.get("trade_date", "the requested date")
        placeholder = HumanMessage(
            content=(
                f"Proceed with your assigned analysis. {instrument_context} "
                f"The analysis date is {trade_date}."
            )
        )
        return {"messages": removals + [placeholder]}

    return delete_messages
