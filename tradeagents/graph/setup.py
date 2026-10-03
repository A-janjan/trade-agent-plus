"""Graph construction.

An analyst registry maps a short name to its node factory, its tools, and the
node names it will occupy in the graph. Adding an analyst is a registry entry;
the graph builder itself does not change.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from tradeagents.agents.analysts.market_analyst import (
    TOOLS as MARKET_TOOLS,
    create_market_analyst,
)
from tradeagents.agents.state import AgentState

ANALYST_REGISTRY: dict[str, dict] = {
    "market": {
        "node": "Market Analyst",
        "tools_node": "tools_market",
        "factory": create_market_analyst,
        "tools": MARKET_TOOLS,
    },
}


def _route_after_analyst(spec: dict, next_node: str):
    """Route to the tools node when the analyst made tool calls, else onward.

    A closure factory rather than a lambda in the loop, so each analyst gets
    its own ``spec``/``next_node`` binding.
    """

    def route(state: AgentState) -> str:
        last_message = state["messages"][-1]
        if spec["tools"] and getattr(last_message, "tool_calls", None):
            return spec["tools_node"]
        return next_node

    return route


def build_graph(selected_analysts, quick_llm, deep_llm=None):
    """Build the analyst chain.

    Analysts run in the order given. Each runs its own ReAct loop; between
    analysts the message list is currently shared.
    """
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
        if spec["tools"]:
            workflow.add_node(spec["tools_node"], ToolNode(list(spec["tools"])))

    workflow.add_edge(START, specs[0]["node"])

    for i, spec in enumerate(specs):
        next_node = specs[i + 1]["node"] if i + 1 < len(specs) else END
        if spec["tools"]:
            workflow.add_conditional_edges(
                spec["node"],
                _route_after_analyst(spec, next_node),
                [spec["tools_node"], next_node],
            )
            workflow.add_edge(spec["tools_node"], spec["node"])
        else:
            workflow.add_edge(spec["node"], next_node)

    return workflow
