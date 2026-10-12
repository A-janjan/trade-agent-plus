"""Reflection generation: one short prose paragraph from a decision and its outcome."""

from __future__ import annotations

from pathlib import Path
from string import Template

from langchain_core.messages import HumanMessage, SystemMessage

_PROMPT = Template(
    (Path(__file__).parent / "prompts" / "reflection.txt").read_text(encoding="utf-8")
)


def generate_reflection(
    llm,
    *,
    ticker: str,
    trade_date: str,
    decision: str,
    raw_return: float,
    alpha_return: float,
    holding_days: int,
    benchmark: str,
) -> str:
    """Return a short reflection as plain prose.

    The prompt is fully determined by its inputs, so the same call is
    reproducible modulo sampling — which matters because reflections are
    cached in the log and re-read by later runs.
    """
    prompt = _PROMPT.substitute(
        ticker=ticker,
        trade_date=trade_date,
        decision=decision,
        raw_return=raw_return,
        alpha_return=alpha_return,
        holding_days=holding_days,
        benchmark=benchmark,
    )
    return llm.invoke(
        [
            SystemMessage(content=prompt),
            HumanMessage(content="Write the reflection now."),
        ]
    ).content
