"""Risk debate: three analysts argue about the size and shape of the trade.

The trader committed to an action; the risk debate is about *how much* to
commit and what could go wrong. Three viewpoints, one mechanism (see
``agents.debate``), one portfolio manager who decides.
"""

from __future__ import annotations

from pathlib import Path

from tradeagents.agents.context import (
    get_portfolio_context_from_state,
    report_or_absent,
)
from tradeagents.agents.debate import create_debate_participant

PROMPTS = Path(__file__).parent / "prompts"

PARTICIPANTS = ["growth", "capital", "balanced"]
NODES = {
    "growth": "Growth Advocate",
    "capital": "Capital Steward",
    "balanced": "Balanced Reviewer",
}


def _risk_evidence(state) -> str:
    """Everything a risk analyst argues from: the four reports, the trader's
    proposal, and the caller's book.

    The trader's proposal is required: it is the subject of the debate. A
    missing proposal is stated so the debaters know the debate is hypothetical,
    not argued against a phantom.
    """
    proposal = (state.get("trader_investment_plan") or "").strip()
    proposal_block = proposal or (
        "(No trader proposal was produced. Argue the risk of the research "
        "plan's direction as if a standard-sized position were on the table.)"
    )
    return "\n\n".join(
        [
            f"### Market\n{report_or_absent(state.get('market_report', ''), 'market')}",
            f"### Sentiment\n{report_or_absent(state.get('sentiment_report', ''), 'sentiment')}",
            f"### News\n{report_or_absent(state.get('news_report', ''), 'news')}",
            f"### Fundamentals\n{report_or_absent(state.get('fundamentals_report', ''), 'fundamentals')}",
            f"### Trader's proposal\n{proposal_block}",
            f"### Caller's book\n{get_portfolio_context_from_state(state)}",
        ]
    )


def create_growth_advocate(llm):
    return create_debate_participant(
        llm,
        prompt_path=PROMPTS / "growth_advocate.txt",
        speaker="growth",
        participants=PARTICIPANTS,
        state_key="risk_debate",
        evidence=_risk_evidence,
    )


def create_capital_steward(llm):
    return create_debate_participant(
        llm,
        prompt_path=PROMPTS / "capital_steward.txt",
        speaker="capital",
        participants=PARTICIPANTS,
        state_key="risk_debate",
        evidence=_risk_evidence,
    )


def create_balanced_reviewer(llm):
    return create_debate_participant(
        llm,
        prompt_path=PROMPTS / "balanced_reviewer.txt",
        speaker="balanced",
        participants=PARTICIPANTS,
        state_key="risk_debate",
        evidence=_risk_evidence,
    )
