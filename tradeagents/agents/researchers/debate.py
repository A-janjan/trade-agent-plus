"""Generic debate participant factory.

A debate participant's job is to argue one side of a question. The shape is
identical for every participant: read the evidence base, read what has been
said, write the next turn. What changes is the role — a text template chosen
by ``role`` and a node name chosen by ``speaker``.

Putting both participants here rather than in separate modules reflects that
they are the same code with different prompts.
"""

from __future__ import annotations

from pathlib import Path
from string import Template

from langchain_core.messages import HumanMessage, SystemMessage

from tradeagents.agents.context import (
    get_language_instruction,
    report_or_absent,
)

_PROMPTS = Path(__file__).parent / "prompts"


def _gather_reports(state) -> str:
    """The four analyst reports, with placeholder markers for missing ones."""
    return "\n\n".join(
        [
            f"### Market\n{report_or_absent(state.get('market_report', ''), 'market')}",
            f"### Sentiment\n{report_or_absent(state.get('sentiment_report', ''), 'sentiment')}",
            f"### News\n{report_or_absent(state.get('news_report', ''), 'news')}",
            f"### Fundamentals\n{report_or_absent(state.get('fundamentals_report', ''), 'fundamentals')}",
        ]
    )


def _render_transcript(transcript: list[dict], participants: list[str]) -> str:
    """Render the debate transcript, with round numbers derived from position.

    A two-participant debate has one turn per speaker per round; the round
    number is ``index // len(participants) + 1``.
    """
    if not transcript:
        return "(No arguments yet — the debate is opening.)"
    per_round = max(1, len(participants))
    lines = []
    for i, turn in enumerate(transcript):
        round_num = i // per_round + 1
        lines.append(f"#### Round {round_num} · {turn['speaker']}\n\n{turn['content']}")
    return "\n\n".join(lines)


def create_debate_participant(llm, role: str, speaker: str, participants: list[str]):
    """Return a node that argues one side of the research debate.

    ``role`` selects the prompt file (``<role>.txt`` under ``prompts/``),
    ``speaker`` is the key stored in the turn, and ``participants`` is the
    ordered list used to derive round numbers.
    """
    template = Template((_PROMPTS / f"{role}.txt").read_text(encoding="utf-8"))

    def node(state):
        debate = state["research_debate"]
        system = template.substitute(
            ticker=state["company_of_interest"],
            trade_date=state["trade_date"],
            instrument_context=state.get("instrument_context", ""),
            evidence=_gather_reports(state),
            transcript=_render_transcript(debate["transcript"], participants),
            language_instruction=get_language_instruction(),
        )
        content = llm.invoke(
            [
                SystemMessage(content=system),
                HumanMessage(content="Write your argument now."),
            ]
        ).content

        turn = {"speaker": speaker, "content": content}
        return {
            "research_debate": {
                **debate,
                "transcript": [*debate["transcript"], turn],
            }
        }

    return node
