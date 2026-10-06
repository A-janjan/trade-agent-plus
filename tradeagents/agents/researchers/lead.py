"""Investment Lead: reads the debate, issues the investment plan.

Where the debate participants argue sides, the lead decides. The verdict is a
structured ``InvestmentPlan`` so downstream consumers (the trader, the risk
debate, the report writer) can read the stance without parsing prose.
"""

from __future__ import annotations

from pathlib import Path
from string import Template

from langchain_core.messages import HumanMessage, SystemMessage

from tradeagents.agents.context import (
    get_language_instruction,
    report_or_absent,
)
from tradeagents.agents.schemas import InvestmentPlan, render_investment_plan
from tradeagents.agents.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)

_PROMPT = Template(
    (Path(__file__).parent / "prompts" / "investment_lead.txt").read_text(
        encoding="utf-8"
    )
)


def _render_transcript(transcript: list[dict]) -> str:
    if not transcript:
        return "(No debate took place — issue your plan on the analyst reports alone.)"
    return "\n\n".join(
        f"#### {turn['speaker']}\n\n{turn['content']}" for turn in transcript
    )


def create_investment_lead(llm):
    structured = bind_structured(llm, InvestmentPlan, "Investment Lead")

    def node(state):
        debate = state["research_debate"]
        evidence = "\n\n".join(
            [
                f"### Market\n{report_or_absent(state.get('market_report', ''), 'market')}",
                f"### Sentiment\n{report_or_absent(state.get('sentiment_report', ''), 'sentiment')}",
                f"### News\n{report_or_absent(state.get('news_report', ''), 'news')}",
                f"### Fundamentals\n{report_or_absent(state.get('fundamentals_report', ''), 'fundamentals')}",
            ]
        )
        system = _PROMPT.substitute(
            ticker=state["company_of_interest"],
            trade_date=state["trade_date"],
            instrument_context=state.get("instrument_context", ""),
            evidence=evidence,
            transcript=_render_transcript(debate["transcript"]),
            language_instruction=get_language_instruction(),
        )
        messages = [
            SystemMessage(content=system),
            HumanMessage(content="Issue the investment plan now."),
        ]
        plan_md = invoke_structured_or_freetext(
            structured, llm, messages, render_investment_plan, "Investment Lead"
        )
        return {
            "investment_plan": plan_md,
            "research_debate": {**debate, "verdict": plan_md},
        }

    return node
