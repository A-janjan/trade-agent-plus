"""Graph construction.

Two registries — analysts and both debates — plus a shared router per debate
family. Adding an analyst is a registry entry; the graph builder itself is
orchestration only.
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
from tradeagents.agents.debate import route_debate
from tradeagents.agents.researchers import (
    NODES as RESEARCH_NODES,
    PARTICIPANTS as RESEARCH_PARTICIPANTS,
    create_downside_case,
    create_upside_case,
)
from tradeagents.agents.researchers.lead import create_investment_lead
from tradeagents.agents.risk import (
    NODES as RISK_NODES,
    PARTICIPANTS as RISK_PARTICIPANTS,
    create_balanced_reviewer,
    create_capital_steward,
    create_growth_advocate,
)
from tradeagents.agents.risk.manager import create_portfolio_manager
from tradeagents.agents.state import AgentState
from tradeagents.agents.trader.trader import create_trader

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
    def route(state: AgentState) -> str:
        last = state["messages"][-1]
        if spec["tools"] and getattr(last, "tool_calls", None):
            return spec["tools_node"]
        return spec["clear_node"]

    return route


def _debate_router(
    *, state_key: str, participants: list[str], nodes: dict[str, str], judge: str
):
    """One graph router per debate. Thin closure around ``route_debate``."""

    def router(state: AgentState) -> str:
        return route_debate(
            state,
            state_key=state_key,
            participants=participants,
            nodes=nodes,
            judge_node=judge,
        )

    return router


def build_graph(selected_analysts, quick_llm, deep_llm):
    """Build the full pipeline: analysts → research debate → trader → risk debate → PM."""
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

    # --- Analysts
    for spec in specs:
        workflow.add_node(spec["node"], spec["factory"](quick_llm))
        workflow.add_node(spec["clear_node"], create_msg_delete())
        if spec["tools"]:
            workflow.add_node(spec["tools_node"], ToolNode(list(spec["tools"])))

    # --- Research debate
    workflow.add_node(RESEARCH_NODES["upside"], create_upside_case(quick_llm))
    workflow.add_node(RESEARCH_NODES["downside"], create_downside_case(quick_llm))
    workflow.add_node("Investment Lead", create_investment_lead(deep_llm))

    # --- Trader
    workflow.add_node("Trader", create_trader(quick_llm))

    # --- Risk debate
    workflow.add_node(RISK_NODES["growth"], create_growth_advocate(quick_llm))
    workflow.add_node(RISK_NODES["capital"], create_capital_steward(quick_llm))
    workflow.add_node(RISK_NODES["balanced"], create_balanced_reviewer(quick_llm))
    workflow.add_node("Portfolio Manager", create_portfolio_manager(deep_llm))

    # --- Edges: analyst chain
    workflow.add_edge(START, specs[0]["node"])
    for i, spec in enumerate(specs):
        next_node = (
            specs[i + 1]["node"] if i + 1 < len(specs) else RESEARCH_NODES["upside"]
        )
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

    # --- Edges: research debate
    research_router = _debate_router(
        state_key="research_debate",
        participants=RESEARCH_PARTICIPANTS,
        nodes=RESEARCH_NODES,
        judge="Investment Lead",
    )
    research_targets = [*RESEARCH_NODES.values(), "Investment Lead"]
    for node_name in RESEARCH_NODES.values():
        workflow.add_conditional_edges(node_name, research_router, research_targets)
    workflow.add_edge("Investment Lead", "Trader")

    # --- Edges: risk debate
    risk_router = _debate_router(
        state_key="risk_debate",
        participants=RISK_PARTICIPANTS,
        nodes=RISK_NODES,
        judge="Portfolio Manager",
    )
    risk_targets = [*RISK_NODES.values(), "Portfolio Manager"]
    for node_name in RISK_NODES.values():
        workflow.add_conditional_edges(node_name, risk_router, risk_targets)

    workflow.add_edge("Trader", RISK_NODES["growth"])
    workflow.add_edge("Portfolio Manager", END)

    return workflow
