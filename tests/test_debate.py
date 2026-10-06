from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage

from tradeagents.agents.researchers.debate import (
    _render_transcript,
    create_debate_participant,
)
from tradeagents.agents.researchers.lead import create_investment_lead
from tradeagents.agents.schemas import InvestmentPlan, Stance, render_investment_plan
from tradeagents.graph.setup import build_graph


class ScriptedLLM:
    """Returns scripted responses in order; accepts bind_tools and
    with_structured_output as no-ops so both plain and structured paths work."""

    def __init__(self, responses):
        self._responses = list(responses)
        self._i = 0

    def bind_tools(self, tools):
        return self

    def with_structured_output(self, schema):
        # Return a callable that yields the next scripted response as if it
        # were a parsed instance of ``schema``.
        def invoke(messages):
            return self._responses[self._i - 1]

        self._invoke_structured = invoke
        return self

    def invoke(self, messages):
        r = self._responses[self._i]
        self._i += 1
        return r


def _state(**overrides):
    state = {
        "company_of_interest": "NVDA",
        "trade_date": "2026-09-01",
        "asset_type": "stock",
        "instrument_context": "The instrument is NVDA.",
        "market_report": "Market says X.",
        "sentiment_report": "",
        "news_report": "News says Y.",
        "fundamentals_report": "",
        "research_debate": {"transcript": [], "max_rounds": 1, "verdict": ""},
    }
    state.update(overrides)
    return state


@pytest.mark.unit
def test_render_transcript_empty():
    assert "no arguments" in _render_transcript([], ["upside", "downside"]).lower()


@pytest.mark.unit
def test_render_transcript_numbers_rounds():
    transcript = [
        {"speaker": "upside", "content": "up 1"},
        {"speaker": "downside", "content": "down 1"},
        {"speaker": "upside", "content": "up 2"},
    ]
    out = _render_transcript(transcript, ["upside", "downside"])
    assert "Round 1" in out and "Round 2" in out
    assert "up 1" in out and "down 1" in out and "up 2" in out


@pytest.mark.unit
def test_debate_participant_appends_turn():
    llm = ScriptedLLM([AIMessage(content="Upside case text.")])
    node = create_debate_participant(
        llm, "upside_case", "upside", ["upside", "downside"]
    )
    out = node(_state())
    turns = out["research_debate"]["transcript"]
    assert len(turns) == 1
    assert turns[0]["speaker"] == "upside"
    assert "Upside case text" in turns[0]["content"]


@pytest.mark.unit
def test_debate_participant_second_turn_appends():
    llm = ScriptedLLM([AIMessage(content="Downside responds.")])
    node = create_debate_participant(
        llm, "downside_case", "downside", ["upside", "downside"]
    )
    state = _state(
        research_debate={
            "transcript": [{"speaker": "upside", "content": "opening"}],
            "max_rounds": 1,
            "verdict": "",
        }
    )
    out = node(state)
    assert len(out["research_debate"]["transcript"]) == 2


@pytest.mark.unit
def test_investment_lead_writes_verdict_and_plan():
    plan = InvestmentPlan(
        stance=Stance.BUY,
        thesis="The bull side wins on the fundamentals.",
        key_risks=["margin compression", "macro slowdown", "competition"],
        catalysts=["earnings", "product launch"],
        conviction="medium",
    )
    llm = ScriptedLLM([plan])
    node = create_investment_lead(llm)
    out = node(_state())
    assert out["investment_plan"] == render_investment_plan(plan)
    assert out["research_debate"]["verdict"] == out["investment_plan"]


@pytest.mark.unit
def test_render_investment_plan_contains_stance_and_thesis():
    plan = InvestmentPlan(
        stance=Stance.SELL,
        thesis="Bear case dominates.",
        key_risks=["a", "b", "c"],
        catalysts=["x"],
        conviction="high",
    )
    text = render_investment_plan(plan)
    assert "**Stance**: Sell" in text
    assert "Bear case dominates." in text
    assert "**Conviction**: High" in text


@pytest.mark.unit
def test_graph_compiles_with_full_pipeline():
    class _AnyLLM:
        def bind_tools(self, tools):
            return self

        def with_structured_output(self, schema):
            return self

        def invoke(self, messages):
            raise NotImplementedError  # graph is only compiled here

    wf = build_graph(("market", "social"), _AnyLLM(), _AnyLLM())
    assert wf.compile() is not None
