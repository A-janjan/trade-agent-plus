"""The event schema the API emits.

Events are flat dicts with a ``type`` field; every type has a fixed shape so
a client can switch on ``type`` and dispatch. Adding a new event type does not
break old clients — they receive and ignore it.

The schema is deliberately decoupled from LangGraph's own event names
(``on_chain_start`` etc.). A LangGraph upgrade that renames its events should
touch one file (the adapter in ``graph/progress.py``), not every client.
"""

from __future__ import annotations

import time
from typing import Any, Literal

EventType = Literal[
    "run.started",
    "run.state",
    "run.finished",
    "run.failed",
    "node.finished",
    "token",
    "tool.started",
    "tool.finished",
    "report",
    "debate.turn",
    "decision",
    "settled",
]

# Node names that produce a report, mapped to the state key that holds it.
# When a node finishes, its output is checked against this table and the
# matching report is emitted as a ``report`` event.
REPORT_NODES: dict[str, str] = {
    "Market Analyst": "market_report",
    "Sentiment Analyst": "sentiment_report",
    "News Analyst": "news_report",
    "Fundamentals Analyst": "fundamentals_report",
    "Investment Lead": "investment_plan",
    "Trader": "trader_investment_plan",
    "Portfolio Manager": "final_trade_decision",
}

# Debate participants, keyed to (debate_state_key, speaker_key).
DEBATE_SPEAKERS: dict[str, tuple[str, str]] = {
    "Upside Case": ("research_debate", "upside"),
    "Downside Case": ("research_debate", "downside"),
    "Growth Advocate": ("risk_debate", "growth"),
    "Capital Steward": ("risk_debate", "capital"),
    "Balanced Reviewer": ("risk_debate", "balanced"),
}


def _now() -> float:
    return time.time()


def run_started(
    run_id: str,
    ticker: str,
    trade_date: str,
    models: dict,
    selected_analysts: list[str] | None = None,
) -> dict:
    return {
        "type": "run.started",
        "ts": _now(),
        "run_id": run_id,
        "ticker": ticker,
        "trade_date": trade_date,
        "models": models,
        "selected_analysts": selected_analysts or [],
    }


def run_finished(run_id: str, rating: str | None, elapsed: float) -> dict:
    return {
        "type": "run.finished",
        "ts": _now(),
        "run_id": run_id,
        "rating": rating,
        "elapsed_seconds": round(elapsed, 2),
    }


def run_failed(run_id: str, error: str) -> dict:
    return {"type": "run.failed", "ts": _now(), "run_id": run_id, "error": error}


def node_finished(node: str) -> dict:
    return {"type": "node.finished", "ts": _now(), "node": node}


def token(node: str, text: str) -> dict:
    return {"type": "token", "ts": _now(), "node": node, "text": text}


def tool_started(node: str, tool: str, args: Any) -> dict:
    return {
        "type": "tool.started",
        "ts": _now(),
        "node": node,
        "tool": tool,
        "args": args,
    }


def tool_finished(node: str, tool: str) -> dict:
    return {"type": "tool.finished", "ts": _now(), "node": node, "tool": tool}


def report(key: str, content: str) -> dict:
    return {"type": "report", "ts": _now(), "key": key, "content": content}


def debate_turn(debate: str, speaker: str, content: str) -> dict:
    return {
        "type": "debate.turn",
        "ts": _now(),
        "debate": debate,
        "speaker": speaker,
        "content": content,
    }


def decision(state: dict) -> dict:
    return {
        "type": "decision",
        "ts": _now(),
        "rating": state.get("final_rating") or None,
        "text": state.get("final_trade_decision") or "",
        "trader_text": state.get("trader_investment_plan") or "",
        "investment_plan": state.get("investment_plan") or "",
    }


def settled(entries: list[dict]) -> dict:
    return {"type": "settled", "ts": _now(), "entries": entries}


def run_state(state: dict) -> dict:
    """The final full state, minus the message list.

    Every report and turn has already been emitted as its own event; this is
    a summary for consumers that want the whole picture at once, or that were
    not connected for the incremental stream. ``messages`` is dropped because
    it carries AIMessage objects whose ``additional_kwargs`` can hold parsed
    Pydantic objects from structured-output calls — not JSON-serializable
    without lossy conversion, and the frontend has no use for them.
    """
    sanitized = {k: v for k, v in state.items() if k != "messages"}
    return {"type": "run.state", "ts": _now(), "state": sanitized}
