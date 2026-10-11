"""Generic debate participant machinery.

A debate is a list of participants who take turns arguing about something,
followed by a judge who decides. That shape is the same whether the topic is
investment direction (two participants) or position risk (three participants),
so the machinery lives here and each debate supplies only its participants,
its evidence gathering, and its prompts.

The transcript is the only state: round number is derived from position, the
next speaker from the last entry. There is no separate counter to fall out of
sync with the transcript, because a counter and a list can only disagree.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from string import Template

from langchain_core.messages import HumanMessage, SystemMessage

from tradeagents.agents.context import get_language_instruction

# ``evidence`` and ``nodes`` are the two knobs a caller sets per debate:
#   evidence(state) -> str      the shared facts the participants argue from
#   nodes          -> {key: name} participant key to graph node name
EvidenceFn = Callable[[dict], str]


def render_transcript(transcript: list[dict], participants: list[str]) -> str:
    """Render a debate transcript with round numbers derived from position.

    With N participants and turns in strict rotation, turn *i* belongs to
    round ``i // N + 1``. Nothing needs to store the round number.
    """
    if not transcript:
        return "(No arguments yet — the debate is opening.)"
    per_round = max(1, len(participants))
    parts = []
    for i, turn in enumerate(transcript):
        round_num = i // per_round + 1
        parts.append(f"#### Round {round_num} · {turn['speaker']}\n\n{turn['content']}")
    return "\n\n".join(parts)


def create_debate_participant(
    llm,
    *,
    prompt_path: Path,
    speaker: str,
    participants: list[str],
    state_key: str,
    evidence: EvidenceFn,
):
    """Return a node that argues one side of a debate.

    The template at ``prompt_path`` is interpolated with ``ticker``,
    ``trade_date``, ``instrument_context``, ``evidence``, ``transcript``, and
    ``language_instruction``. The node appends one turn to the transcript at
    ``state_key``; it does not decide who speaks next — the router does, from
    the transcript it just appended to.
    """
    template = Template(prompt_path.read_text(encoding="utf-8"))

    def node(state):
        debate = state[state_key]
        system = template.substitute(
            ticker=state["company_of_interest"],
            trade_date=state["trade_date"],
            instrument_context=state.get("instrument_context", ""),
            evidence=evidence(state),
            transcript=render_transcript(debate["transcript"], participants),
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
            state_key: {**debate, "transcript": [*debate["transcript"], turn]},
        }

    return node


def route_debate(
    state,
    *,
    state_key: str,
    participants: list[str],
    nodes: dict[str, str],
    judge_node: str,
) -> str:
    """Next speaker's graph node, or the judge when the debate is exhausted.

    A debate lasts ``max_rounds`` rotations through ``participants``. The
    first turn goes to ``participants[0]``; each subsequent turn goes to the
    one after the last speaker.
    """
    debate = state[state_key]
    transcript = debate["transcript"]
    if len(transcript) >= len(participants) * debate["max_rounds"]:
        return judge_node
    if not transcript:
        return nodes[participants[0]]
    last = transcript[-1]["speaker"]
    idx = participants.index(last)
    next_key = participants[(idx + 1) % len(participants)]
    return nodes[next_key]
