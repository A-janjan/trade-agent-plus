from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from tradeagents.agents.analysts.fundamentals_analyst import create_fundamentals_analyst
from tradeagents.agents.analysts.news_analyst import create_news_analyst
from tradeagents.agents.context import create_msg_delete, report_or_absent
from tradeagents.graph.setup import build_graph


class StubLLM:
    def __init__(self, responses):
        self._responses = list(responses)
        self._i = 0

    def bind_tools(self, tools):
        self._tools = tools
        return self

    def invoke(self, messages):
        r = self._responses[self._i]
        self._i += 1
        return r


def _base_state(**overrides):
    state = {
        "messages": [HumanMessage(content="go")],
        "company_of_interest": "NVDA",
        "trade_date": "2026-09-01",
        "asset_type": "stock",
        "instrument_context": "The instrument is NVDA.",
    }
    state.update(overrides)
    return state


@pytest.mark.unit
def test_fundamentals_analyst_emits_report():
    llm = StubLLM([AIMessage(content="# Fundamentals\nGood.")])
    node = create_fundamentals_analyst(llm)
    out = node(_base_state())
    assert out["fundamentals_report"] == "# Fundamentals\nGood."
    assert out["sender"] == "fundamentals_analyst"


@pytest.mark.unit
def test_news_analyst_emits_report():
    llm = StubLLM([AIMessage(content="# News\nOK.")])
    node = create_news_analyst(llm)
    out = node(_base_state())
    assert out["news_report"] == "# News\nOK."
    assert out["sender"] == "news_analyst"


@pytest.mark.unit
def test_report_or_absent_returns_text_when_present():
    assert report_or_absent("hello", "market") == "hello"


@pytest.mark.unit
def test_report_or_absent_returns_marker_when_empty():
    out = report_or_absent("", "market")
    assert "No market report" in out
    assert "not an empty finding" in out


@pytest.mark.unit
def test_create_msg_delete_removes_all_and_adds_placeholder():
    delete = create_msg_delete()
    state = _base_state()
    out = delete(state)
    # All original messages removed, one placeholder added.
    assert len(out["messages"]) == 2  # one RemoveMessage per existing + placeholder
    placeholder = out["messages"][-1]
    assert "NVDA" in placeholder.content
    assert "2026-09-01" in placeholder.content


@pytest.mark.unit
def test_graph_compiles_with_all_analysts():
    llm = StubLLM([AIMessage(content="report")] * 10)
    wf = build_graph(("market", "social", "news", "fundamentals"), llm)
    assert wf.compile() is not None


@pytest.mark.unit
def test_graph_rejects_unknown_analyst():
    llm = StubLLM([])
    with pytest.raises(ValueError, match="Unknown analyst"):
        build_graph(("not_a_real_analyst",), llm)
