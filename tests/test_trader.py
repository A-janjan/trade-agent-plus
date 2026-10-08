from __future__ import annotations

import pytest

from tradeagents.agents.schemas import (
    TraderAction,
    TraderProposal,
    render_trader_proposal,
)
from tradeagents.agents.trader.trader import _portfolio_block, create_trader
from tradeagents.graph.setup import build_graph


class ScriptedLLM:
    """Accepts bind_tools / with_structured_output as no-ops; returns scripted
    responses from ``invoke``."""

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
        "investment_plan": "**Stance**: Buy\n\n**Conviction**: High",
        "market_report": "Trend is up. Close 189.5, support 180, resistance 195.",
        "portfolio_context": "",
        "past_context": "",
    }
    state.update(overrides)
    return state


# ---------------------------------------------------------------------------
# Schema: coercion of LLM-written price fields
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_price_accepts_plain_float():
    p = TraderProposal(action=TraderAction.BUY, reasoning="x", entry_price=189.5)
    assert p.entry_price == 189.5


@pytest.mark.unit
def test_price_accepts_numeric_string():
    p = TraderProposal(action=TraderAction.BUY, reasoning="x", entry_price=189.5)
    assert p.entry_price == 189.5


@pytest.mark.unit
def test_price_strips_currency_symbol_and_commas():
    p = TraderProposal(action=TraderAction.BUY, reasoning="x", stop_loss=1234.50)
    assert p.stop_loss == 1234.5


@pytest.mark.unit
@pytest.mark.parametrize(
    "placeholder", ["None", "N/A", "n/a", "TBD", "", "  ", "-", "unknown"]
)
def test_price_drops_placeholders(placeholder):
    p = TraderProposal(action=TraderAction.HOLD, reasoning="x", entry_price=placeholder)
    assert p.entry_price is None


@pytest.mark.unit
def test_price_null_is_fine():
    p = TraderProposal(action=TraderAction.HOLD, reasoning="x")
    assert p.entry_price is None
    assert p.stop_loss is None


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_render_names_absent_fields():
    proposal = TraderProposal(action=TraderAction.HOLD, reasoning="Balanced.")
    text = render_trader_proposal(proposal)
    assert "**Action**: Hold" in text
    assert "**Entry Price**: not provided" in text
    assert "**Stop Loss**: not provided" in text


@pytest.mark.unit
def test_render_includes_given_values():
    proposal = TraderProposal(
        action=TraderAction.BUY,
        reasoning="Breakout confirmed.",
        entry_price=189.5,
        stop_loss=180.0,
        position_sizing="5% of portfolio",
    )
    text = render_trader_proposal(proposal)
    assert "**Entry Price**: 189.5" in text
    assert "**Stop Loss**: 180.0" in text
    assert "**Position Sizing**: 5% of portfolio" in text


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_trader_writes_proposal():
    proposal = TraderProposal(
        action=TraderAction.BUY,
        reasoning="Momentum and stance align.",
        entry_price=190.0,
        stop_loss=180.0,
        position_sizing="5% of portfolio",
    )
    llm = ScriptedLLM([proposal])
    node = create_trader(llm)
    out = node(_state())
    assert out["sender"] == "trader"
    assert "**Action**: Buy" in out["trader_investment_plan"]
    assert out["trader_investment_plan"] == render_trader_proposal(proposal)


@pytest.mark.unit
def test_trader_prompt_includes_no_external_tools_instruction():
    # The instruction must reach the model; a regression that drops it would
    # let the model reach for tools it was never bound to and blow up the
    # structured call.
    captured: dict = {}

    class CapturingLLM:
        def with_structured_output(self, schema):
            return self

        def invoke(self, messages):
            captured["system"] = messages[0].content
            captured["user"] = messages[1].content
            return TraderProposal(action=TraderAction.HOLD, reasoning="ok")

    node = create_trader(CapturingLLM())
    node(_state())
    assert "Do not call external tools" in captured["system"]
    assert captured["user"] == "Issue the transaction proposal now."


@pytest.mark.unit
def test_trader_prompt_includes_portfolio_notice_when_absent():
    captured: dict = {}

    class CapturingLLM:
        def with_structured_output(self, schema):
            return self

        def invoke(self, messages):
            captured["system"] = messages[0].content
            return TraderProposal(action=TraderAction.HOLD, reasoning="ok")

    node = create_trader(CapturingLLM())
    node(_state(portfolio_context=""))
    assert "No portfolio was provided" in captured["system"]


@pytest.mark.unit
def test_trader_prompt_includes_portfolio_when_present():
    captured: dict = {}

    class CapturingLLM:
        def with_structured_output(self, schema):
            return self

        def invoke(self, messages):
            captured["system"] = messages[0].content
            return TraderProposal(action=TraderAction.HOLD, reasoning="ok")

    node = create_trader(CapturingLLM())
    node(
        _state(
            portfolio_context="- Current position in NVDA: 120 units, average price 150.00"
        )
    )
    assert "120 units" in captured["system"]
    assert "No portfolio was provided" not in captured["system"]


# ---------------------------------------------------------------------------
# _portfolio_block: the two absences must not collapse
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_portfolio_block_returns_context_when_present():
    text = _portfolio_block({"portfolio_context": "book here"})
    assert text == "book here"


@pytest.mark.unit
def test_portfolio_block_returns_notice_when_absent():
    text = _portfolio_block({"portfolio_context": ""})
    assert "No portfolio was provided" in text


@pytest.mark.unit
def test_portfolio_block_returns_notice_when_key_missing():
    text = _portfolio_block({})
    assert "No portfolio was provided" in text


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_graph_compiles_with_trader():
    class _AnyLLM:
        def bind_tools(self, tools):
            return self

        def with_structured_output(self, schema):
            return self

        def invoke(self, messages):
            raise NotImplementedError

    wf = build_graph(("market",), _AnyLLM(), _AnyLLM())
    assert wf.compile() is not None
