from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage

from tradeagents.agents.debate import (
    create_debate_participant,
    render_transcript,
    route_debate,
)


class ScriptedLLM:
    def __init__(self, responses):
        self._responses = list(responses)
        self._i = 0

    def invoke(self, messages):
        r = self._responses[self._i]
        self._i += 1
        return r


@pytest.fixture
def prompt_file(tmp_path):
    p = tmp_path / "role.txt"
    p.write_text(
        "Role for ${ticker} on ${trade_date}. Evidence:\n${evidence}\n"
        "Transcript:\n${transcript}\n${language_instruction}",
        encoding="utf-8",
    )
    return p


def _state(transcript=None, max_rounds=1):
    return {
        "company_of_interest": "NVDA",
        "trade_date": "2026-09-01",
        "instrument_context": "",
        "test_debate": {
            "transcript": transcript or [],
            "max_rounds": max_rounds,
            "verdict": "",
        },
    }


# ---- render_transcript ----


@pytest.mark.unit
def test_render_transcript_marks_opening():
    assert "no arguments" in render_transcript([], ["a", "b"]).lower()


@pytest.mark.unit
def test_render_transcript_derives_round_from_position():
    transcript = [
        {"speaker": "a", "content": "a1"},
        {"speaker": "b", "content": "b1"},
        {"speaker": "a", "content": "a2"},
    ]
    out = render_transcript(transcript, ["a", "b"])
    assert "Round 1 · a" in out
    assert "Round 1 · b" in out
    assert "Round 2 · a" in out


@pytest.mark.unit
def test_render_transcript_three_participant_rounds():
    transcript = [
        {"speaker": "a", "content": "a1"},
        {"speaker": "b", "content": "b1"},
        {"speaker": "c", "content": "c1"},
        {"speaker": "a", "content": "a2"},
    ]
    out = render_transcript(transcript, ["a", "b", "c"])
    assert "Round 1 · c" in out
    assert "Round 2 · a" in out


# ---- create_debate_participant ----


@pytest.mark.unit
def test_participant_appends_one_turn(prompt_file):
    llm = ScriptedLLM([AIMessage(content="here is my case")])
    node = create_debate_participant(
        llm,
        prompt_path=prompt_file,
        speaker="a",
        participants=["a", "b"],
        state_key="test_debate",
        evidence=lambda s: "evidence text",
    )
    out = node(_state())
    transcript = out["test_debate"]["transcript"]
    assert len(transcript) == 1
    assert transcript[0]["speaker"] == "a"
    assert transcript[0]["content"] == "here is my case"


@pytest.mark.unit
def test_participant_preserves_existing_turns(prompt_file):
    llm = ScriptedLLM([AIMessage(content="second")])
    node = create_debate_participant(
        llm,
        prompt_path=prompt_file,
        speaker="b",
        participants=["a", "b"],
        state_key="test_debate",
        evidence=lambda s: "",
    )
    out = node(_state(transcript=[{"speaker": "a", "content": "first"}]))
    transcript = out["test_debate"]["transcript"]
    assert len(transcript) == 2
    assert transcript[0]["content"] == "first"
    assert transcript[1]["content"] == "second"


# ---- route_debate ----


@pytest.mark.unit
def test_router_opens_with_first_participant():
    state = _state()
    result = route_debate(
        state,
        state_key="test_debate",
        participants=["a", "b"],
        nodes={"a": "A", "b": "B"},
        judge_node="Judge",
    )
    assert result == "A"


@pytest.mark.unit
def test_router_alternates_participants():
    state = _state(transcript=[{"speaker": "a", "content": ""}])
    result = route_debate(
        state,
        state_key="test_debate",
        participants=["a", "b"],
        nodes={"a": "A", "b": "B"},
        judge_node="Judge",
    )
    assert result == "B"


@pytest.mark.unit
def test_router_three_participant_rotation():
    state = _state(
        transcript=[
            {"speaker": "a", "content": ""},
            {"speaker": "b", "content": ""},
        ]
    )
    result = route_debate(
        state,
        state_key="test_debate",
        participants=["a", "b", "c"],
        nodes={"a": "A", "b": "B", "c": "C"},
        judge_node="Judge",
    )
    assert result == "C"


@pytest.mark.unit
def test_router_routes_to_judge_when_max_rounds_reached():
    transcript = [
        {"speaker": "a", "content": ""},
        {"speaker": "b", "content": ""},
    ]
    state = _state(transcript=transcript, max_rounds=1)
    result = route_debate(
        state,
        state_key="test_debate",
        participants=["a", "b"],
        nodes={"a": "A", "b": "B"},
        judge_node="Judge",
    )
    assert result == "Judge"


@pytest.mark.unit
def test_router_runs_second_round_when_configured():
    transcript = [
        {"speaker": "a", "content": ""},
        {"speaker": "b", "content": ""},
    ]
    state = _state(transcript=transcript, max_rounds=2)
    result = route_debate(
        state,
        state_key="test_debate",
        participants=["a", "b"],
        nodes={"a": "A", "b": "B"},
        judge_node="Judge",
    )
    assert result == "A"
