"""Trader: convert an investment plan into a concrete transaction proposal.

The trader is a synthesis node, not an investigation node. It has no tools and
does not read the message history — its whole input is three strings injected
into one prompt (the plan, the technical report, the caller's book) and its
whole output is one structured ``TraderProposal``. That shape is deliberate:
a trader that reaches for more data is a trader that has not decided.
"""

from __future__ import annotations

from pathlib import Path
from string import Template

from langchain_core.messages import HumanMessage, SystemMessage

from tradeagents.agents.context import (
    get_language_instruction,
    report_or_absent,
)
from tradeagents.agents.schemas import TraderProposal, render_trader_proposal
from tradeagents.agents.structured import (
    NO_EXTERNAL_TOOLS,
    bind_structured,
    invoke_structured_or_freetext,
)

_PROMPT = Template(
    (Path(__file__).parent / "prompts" / "trader.txt").read_text(encoding="utf-8")
)

_NO_PORTFOLIO = (
    "No portfolio was provided for this run. Size against a standard "
    "allocation and do not assume the caller holds a flat book."
)


def _portfolio_block(state) -> str:
    """The caller's book, or a notice that none was given.

    Absence and flatness are different claims about an account. Passing an
    empty string through would read to the model as a flat book, which is a
    fact nobody told us.
    """
    context = (state.get("portfolio_context") or "").strip()
    return context if context else _NO_PORTFOLIO


def create_trader(llm):
    """Return a trader node bound to ``llm``."""
    structured = bind_structured(llm, TraderProposal, "Trader")

    def trader_node(state):
        prompt = _PROMPT.substitute(
            ticker=state["company_of_interest"],
            trade_date=state["trade_date"],
            instrument_context=state.get("instrument_context", ""),
            investment_plan=state.get("investment_plan", "")
            or "(No investment plan was produced; the research debate did not conclude.)",
            market_report=report_or_absent(state.get("market_report", ""), "market"),
            portfolio_context=_portfolio_block(state),
            language_instruction=get_language_instruction(),
        )
        # NO_EXTERNAL_TOOLS goes in as a final paragraph rather than the top:
        # the model reads the mandate first, then the boundary on how to fulfil
        # it, which is how a brief reads on a desk.
        prompt = f"{prompt}\n\n{NO_EXTERNAL_TOOLS}"

        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content="Issue the transaction proposal now."),
        ]
        proposal_md = invoke_structured_or_freetext(
            structured,
            llm,
            messages,
            render_trader_proposal,
            "Trader",
        )
        return {
            "trader_investment_plan": proposal_md,
            "sender": "trader",
        }

    return trader_node
