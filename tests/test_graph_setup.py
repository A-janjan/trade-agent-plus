from __future__ import annotations

import pytest

from tradeagents.graph.setup import build_graph


class _NoOpLLM:
    def bind_tools(self, tools):
        return self

    def invoke(self, messages):  # pragma: no cover — the graph is only compiled here
        raise NotImplementedError


@pytest.mark.unit
def test_graph_compiles_with_market_analyst():
    workflow = build_graph(("market",), _NoOpLLM())
    compiled = workflow.compile()
    assert compiled is not None


@pytest.mark.unit
def test_graph_rejects_unknown_analyst():
    with pytest.raises(ValueError, match="Unknown analyst"):
        build_graph(("fundamentals",), _NoOpLLM())


@pytest.mark.unit
def test_graph_rejects_empty_selection():
    with pytest.raises(ValueError, match="At least one analyst"):
        build_graph((), _NoOpLLM())
