from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from tradeagents.agents.analysts.market_analyst import create_market_analyst


class StubLLM:
    """Minimal stand-in: returns queued responses, satisfies bind_tools()."""

    def __init__(self, responses):
        self._responses = list(responses)
        self._i = 0

    def bind_tools(self, tools):
        self._tools = tools
        return self

    def invoke(self, messages):
        response = self._responses[self._i]
        self._i += 1
        return response


def _state(messages):
    return {
        "messages": messages,
        "company_of_interest": "NVDA",
        "trade_date": "2026-09-01",
        "asset_type": "stock",
        "instrument_context": "The instrument is NVDA.",
    }


@pytest.mark.unit
def test_market_analyst_emits_report_when_no_tool_calls():
    llm = StubLLM([AIMessage(content="# Market report\n\nTrend is up.")])
    node = create_market_analyst(llm)

    out = node(_state([HumanMessage(content="Analyze NVDA as of 2026-09-01.")]))

    assert out["market_report"] == "# Market report\n\nTrend is up."
    assert out["sender"] == "market_analyst"
    assert len(out["messages"]) == 1


@pytest.mark.unit
def test_market_analyst_returns_empty_report_when_tool_calls_pending():
    call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "get_stock_data",
                "args": {
                    "symbol": "NVDA",
                    "start_date": "2026-06-01",
                    "end_date": "2026-09-01",
                },
                "id": "call_1",
            }
        ],
    )
    llm = StubLLM([call])
    node = create_market_analyst(llm)

    out = node(_state([HumanMessage(content="Analyze NVDA as of 2026-09-01.")]))

    # The loop is not done yet, so no report is written this turn.
    assert out["market_report"] == ""
    assert out["messages"][-1].tool_calls
