"""Graph construction.

An analyst registry maps a short name to its node factory, its tools, and the
node names it will occupy. Adding an analyst is a registry entry; the graph
builder itself does not change. Between analysts, a clear node wipes the
message list so the next analyst sees only a fresh, context-anchored prompt.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from tradeagents.agents.analysts.fundamentals_analyst import (
    TOOLS as FUNDAMENTALS_TOOLS,
    create_fundamentals_analyst,
)
from tradeagents.agents.analysts.market_analyst import (
    TOOLS as MARKET_TOOLS,
    create_market_analyst,
)
from tradeagents.agents.analysts.news_analyst import (
    TOOLS as NEWS_TOOLS,
    create_news_analyst,
)
from tradeagents.agents.analysts.sentiment_analyst import create_sentiment_analyst
from tradeagents.agents.context import create_msg_delete
from tradeagents.agents.state import AgentState

ANALYST_REGISTRY: dict[str, dict] = {
    "market": {
        "node": "Market Analyst",
        "tools_node": "tools_market",
        "clear_node": "Clear Market",
        "factory": create_market_analyst,
        "tools": MARKET_TOOLS,
    },
    "social": {
        "node": "Sentiment Analyst",
        "tools_node": None,
        "clear_node": "Clear Sentiment",
        "factory": create_sentiment_analyst,
        "tools": (),
    },
    "news": {
        "node": "News Analyst",
        "tools_node": "tools_news",
        "clear_node": "Clear News",
        "factory": create_news_analyst,
        "tools": NEWS_TOOLS,
    },
    "fundamentals": {
        "node": "Fundamentals Analyst",
        "tools_node": "tools_fundamentals",
        "clear_node": "Clear Fundamentals",
        "factory": create_fundamentals_analyst,
        "tools": FUNDAMENTALS_TOOLS,
    },
}


def _route_after_analyst(spec: dict):
    """Route to the tools node while the analyst still has pending tool calls,
    else to its clear node."""

    def route(state: AgentState) -> str:
        last = state["messages"][-1]
        if spec["tools"] and getattr(last, "tool_calls", None):
            return spec["tools_node"]
        return spec["clear_node"]

    return route


def build_graph(selected_analysts, quick_llm, deep_llm=None):
    """Build the analyst chain with per-analyst clear nodes between them."""
    specs: list[dict] = []
    for name in selected_analysts:
        if name not in ANALYST_REGISTRY:
            raise ValueError(
                f"Unknown analyst {name!r}. Registered: {list(ANALYST_REGISTRY)}"
            )
        specs.append(ANALYST_REGISTRY[name])
    if not specs:
        raise ValueError("At least one analyst must be selected")

    workflow = StateGraph(AgentState)

    for spec in specs:
        workflow.add_node(spec["node"], spec["factory"](quick_llm))
        workflow.add_node(spec["clear_node"], create_msg_delete())
        if spec["tools"]:
            workflow.add_node(spec["tools_node"], ToolNode(list(spec["tools"])))

    workflow.add_edge(START, specs[0]["node"])

    for i, spec in enumerate(specs):
        next_node = specs[i + 1]["node"] if i + 1 < len(specs) else END
        if spec["tools"]:
            workflow.add_conditional_edges(
                spec["node"],
                _route_after_analyst(spec),
                [spec["tools_node"], spec["clear_node"]],
            )
            workflow.add_edge(spec["tools_node"], spec["node"])
        else:
            workflow.add_edge(spec["node"], spec["clear_node"])
        workflow.add_edge(spec["clear_node"], next_node)

    return workflow
