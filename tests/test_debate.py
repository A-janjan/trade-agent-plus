from __future__ import annotations

import pytest

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
