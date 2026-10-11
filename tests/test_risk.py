from __future__ import annotations

import pytest

from tradeagents.agents.risk import _risk_evidence
from tradeagents.agents.risk.manager import create_portfolio_manager
from tradeagents.agents.schemas import (
    PortfolioDecision,
    Stance,
    render_pm_decision,
)
from tradeagents.graph.setup import build_graph


class ScriptedLLM:
    def __init__(self, responses):
        self._responses = list(responses)
        self._i = 0

    def bind_tools(self, tools):
        return self

    def with_structured_output(self, schema):
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
        "portfolio_context": "",
        "market_report": "Trend up.",
        "sentiment_report": "",
        "news_report": "Macro mixed.",
        "fundamentals_report": "Margins strong.",
        "investment_plan": "**Stance**: Buy",
        "trader_investment_plan": "**Action**: Buy\n\n**Entry Price**: 190.0",
        "past_context": "",
        "risk_debate": {"transcript": [], "max_rounds": 1, "verdict": ""},
    }
    state.update(overrides)
    return state


# ---- _risk_evidence ----


@pytest.mark.unit
def test_risk_evidence_includes_trader_proposal():
    text = _risk_evidence(_state())
    assert "**Action**: Buy" in text
    assert "Trader's proposal" in text


@pytest.mark.unit
def test_risk_evidence_states_missing_proposal_explicitly():
    text = _risk_evidence(_state(trader_investment_plan=""))
    assert "No trader proposal was produced" in text


@pytest.mark.unit
def test_risk_evidence_includes_portfolio_notice_when_absent():
    text = _risk_evidence(_state(portfolio_context=""))
    assert "No portfolio was provided" in text


# ---- PM schema and renderer ----


@pytest.mark.unit
def test_pm_decision_accepts_plain_rating():
    d = PortfolioDecision(
        rating=Stance.BUY,
        executive_summary="Enter at 190.",
        investment_thesis="Debate settled on the bull side.",
    )
    assert d.rating == Stance.BUY


@pytest.mark.unit
def test_pm_decision_coerces_price_target():
    d = PortfolioDecision(
        rating=Stance.BUY,
        executive_summary="x",
        investment_thesis="y",
        price_target=1234.50,
    )
    assert d.price_target == 1234.5



@pytest.mark.unit
def test_render_pm_decision_has_stable_labels():
    d = PortfolioDecision(
        rating=Stance.HOLD,
        executive_summary="Maintain.",
        investment_thesis="Balanced.",
    )
    text = render_pm_decision(d)
    assert "**Rating**: Hold" in text
    assert "**Executive Summary**: Maintain." in text
    assert "**Investment Thesis**: Balanced." in text
    assert "**Price Target**: not provided" in text
    assert "**Time Horizon**: not provided" in text


# ---- PM node ----


@pytest.mark.unit
def test_pm_node_writes_decision_and_verdict():
    decision = PortfolioDecision(
        rating=Stance.BUY,
        executive_summary="Enter at 190.",
        investment_thesis="Growth case won.",
        price_target=210.0,
        time_horizon="3-6 months",
    )
    llm = ScriptedLLM([decision])
    node = create_portfolio_manager(llm)
    out = node(_state())
    assert out["sender"] == "portfolio_manager"
    assert out["final_trade_decision"] == render_pm_decision(decision)
    assert out["risk_debate"]["verdict"] == out["final_trade_decision"]


@pytest.mark.unit
def test_pm_prompt_includes_risk_debate_transcript():
    captured: dict = {}

    class CapturingLLM:
        def with_structured_output(self, schema):
            return self

        def invoke(self, messages):
            captured["system"] = messages[0].content
            return PortfolioDecision(
                rating=Stance.HOLD, executive_summary="x", investment_thesis="y"
            )

    state = _state(
        risk_debate={
            "transcript": [
                {"speaker": "growth", "content": "Go big."},
                {"speaker": "capital", "content": "Go small."},
                {"speaker": "balanced", "content": "Middle."},
            ],
            "max_rounds": 1,
            "verdict": "",
        }
    )
    node = create_portfolio_manager(CapturingLLM())
    node(state)
    assert "Go big." in captured["system"]
    assert "Go small." in captured["system"]
    assert "Middle." in captured["system"]


@pytest.mark.unit
def test_pm_prompt_includes_no_external_tools_instruction():
    captured: dict = {}

    class CapturingLLM:
        def with_structured_output(self, schema):
            return self

        def invoke(self, messages):
            captured["system"] = messages[0].content
            return PortfolioDecision(
                rating=Stance.HOLD, executive_summary="x", investment_thesis="y"
            )

    node = create_portfolio_manager(CapturingLLM())
    node(_state())
    assert "Do not call external tools" in captured["system"]


# ---- Graph ----


@pytest.mark.unit
def test_graph_compiles_with_full_pipeline():
    class _AnyLLM:
        def bind_tools(self, tools):
            return self

        def with_structured_output(self, schema):
            return self

        def invoke(self, messages):
            raise NotImplementedError

    wf = build_graph(("market", "social"), _AnyLLM(), _AnyLLM())
    assert wf.compile() is not None
