"""Research debate: two analysts argue for and against the instrument.

The mechanics live in ``agents.debate``; this package supplies the two
prompts, the participant keys, and the evidence the debaters argue from.
"""

from __future__ import annotations

from pathlib import Path

from tradeagents.agents.context import report_or_absent
from tradeagents.agents.debate import create_debate_participant

PROMPTS = Path(__file__).parent / "prompts"

# Participant keys in speaking order. The router derives the next speaker from
# the last entry in the transcript, so this list is the only place the rotation
# is defined.
PARTICIPANTS = ["upside", "downside"]
NODES = {"upside": "Upside Case", "downside": "Downside Case"}


def _analyst_evidence(state) -> str:
    """The four analyst reports, with explicit markers for missing ones.

    A blank section in the prompt reads to a model as "the analyst found
    nothing", which is a finding. ``report_or_absent`` distinguishes "not
    selected" from "produced nothing" so a debater cannot argue from absence.
    """
    return "\n\n".join(
        [
            f"### Market\n{report_or_absent(state.get('market_report', ''), 'market')}",
            f"### Sentiment\n{report_or_absent(state.get('sentiment_report', ''), 'sentiment')}",
            f"### News\n{report_or_absent(state.get('news_report', ''), 'news')}",
            f"### Fundamentals\n{report_or_absent(state.get('fundamentals_report', ''), 'fundamentals')}",
        ]
    )


def create_upside_case(llm):
    return create_debate_participant(
        llm,
        prompt_path=PROMPTS / "upside_case.txt",
        speaker="upside",
        participants=PARTICIPANTS,
        state_key="research_debate",
        evidence=_analyst_evidence,
    )


def create_downside_case(llm):
    return create_debate_participant(
        llm,
        prompt_path=PROMPTS / "downside_case.txt",
        speaker="downside",
        participants=PARTICIPANTS,
        state_key="research_debate",
        evidence=_analyst_evidence,
    )
