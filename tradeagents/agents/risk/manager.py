"""Portfolio Manager: issue the final rating.

The PM reads everything the pipeline produced — the research plan, the
trader's proposal, the risk debate — and produces the run's actual output: a
5-tier rating, an action summary, and the thesis behind it. It is the last
node, and the only one whose decision is logged and reflected on in Phase 8.
"""

from __future__ import annotations

from pathlib import Path
from string import Template

from langchain_core.messages import HumanMessage, SystemMessage

from tradeagents.agents.context import (
    get_instrument_context_from_state,
    get_language_instruction,
    get_portfolio_context_from_state,
)
from tradeagents.agents.debate import render_transcript
from tradeagents.agents.risk import PARTICIPANTS
from tradeagents.agents.schemas import PortfolioDecision, render_pm_decision
from tradeagents.agents.structured import (
    NO_EXTERNAL_TOOLS,
    bind_structured,
    invoke_structured_or_freetext,
)

_PROMPT = Template(
    (Path(__file__).parent / "prompts" / "portfolio_manager.txt").read_text(
        encoding="utf-8"
    )
)


def create_portfolio_manager(llm):
    structured = bind_structured(llm, PortfolioDecision, "Portfolio Manager")

    def node(state):
        debate = state["risk_debate"]
        prompt = (
            _PROMPT.substitute(
                ticker=state["company_of_interest"],
                trade_date=state["trade_date"],
                instrument_context=get_instrument_context_from_state(state),
                portfolio_context=get_portfolio_context_from_state(state),
                investment_plan=state.get("investment_plan", "")
                or "(No investment plan was produced.)",
                trader_proposal=state.get("trader_investment_plan", "")
                or "(No trader proposal was produced.)",
                risk_debate=render_transcript(debate["transcript"], PARTICIPANTS),
                past_context=(state.get("past_context") or "").strip()
                or "(No prior lessons.)",
                language_instruction=get_language_instruction(),
            )
            + f"\n\n{NO_EXTERNAL_TOOLS}"
        )

        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content="Issue the final decision now."),
        ]
        decision_md = invoke_structured_or_freetext(
            structured,
            llm,
            messages,
            render_pm_decision,
            "Portfolio Manager",
        )
        return {
            "final_trade_decision": decision_md,
            "risk_debate": {**debate, "verdict": decision_md},
            "sender": "portfolio_manager",
        }

    return node
