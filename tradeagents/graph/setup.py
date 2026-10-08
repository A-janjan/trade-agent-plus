"""Graph construction.

Two registries — analysts and debate participants — plus a shared router for
each debate. Adding an analyst is a registry entry; adding a debate is a
router. The graph builder itself is orchestration only.
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
from tradeagents.agents.researchers.debate import create_debate_participant
from tradeagents.agents.researchers.lead import create_investment_lead
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

# Ordered participants for the research debate.
RESEARCH_DEBATE_PARTICIPANTS = ["upside", "downside"]
RESEARCH_DEBATE_NODES = {"upside": "Upside Case", "downside": "Downside Case"}


def _route_after_analyst(spec: dict):
    def route(state: AgentState) -> str:
        last = state["messages"][-1]
        if spec["tools"] and getattr(last, "tool_calls", None):
            return spec["tools_node"]
        return spec["clear_node"]

    return route


def _route_debate(
    state: AgentState, participants: list[str], state_key: str, limit_node: str
):
    """Route to the next participant, or to the judge when rounds are exhausted."""
    debate = state[state_key]
    transcript = debate["transcript"]
    if len(transcript) >= len(participants) * debate["max_rounds"]:
        return limit_node
    if not transcript:
        return (
            RESEARCH_DEBATE_NODES[participants[0]]
            if state_key == "research_debate"
            else participants[0]
        )
    last_speaker = transcript[-1]["speaker"]
    idx = participants.index(last_speaker)
    next_speaker = participants[(idx + 1) % len(participants)]
    return (
        RESEARCH_DEBATE_NODES[next_speaker]
        if state_key == "research_debate"
        else next_speaker
    )


def build_graph(selected_analysts, quick_llm, deep_llm):
    """Build the full pipeline: analysts, then research debate, then verdict."""
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

    # Analysts
    for spec in specs:
        workflow.add_node(spec["node"], spec["factory"](quick_llm))
        workflow.add_node(spec["clear_node"], create_msg_delete())
        if spec["tools"]:
            workflow.add_node(spec["tools_node"], ToolNode(list(spec["tools"])))

    # Research debate
    workflow.add_node(
        "Upside Case",
        create_debate_participant(
            quick_llm, "upside_case", "upside", RESEARCH_DEBATE_PARTICIPANTS
        ),
    )
    workflow.add_node(
        "Downside Case",
        create_debate_participant(
            quick_llm, "downside_case", "downside", RESEARCH_DEBATE_PARTICIPANTS
        ),
    )
    workflow.add_node("Investment Lead", create_investment_lead(deep_llm))
    workflow.add_node("Trader", create_trader(quick_llm))

    # Edges: analyst chain
    workflow.add_edge(START, specs[0]["node"])
    for i, spec in enumerate(specs):
        next_node = specs[i + 1]["node"] if i + 1 < len(specs) else "Upside Case"
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

    # Edges: research debate
    debate_choices = [
        RESEARCH_DEBATE_NODES[p] for p in RESEARCH_DEBATE_PARTICIPANTS
    ] + ["Investment Lead"]
    workflow.add_conditional_edges(
        "Upside Case",
        lambda s: _route_debate(
            s, RESEARCH_DEBATE_PARTICIPANTS, "research_debate", "Investment Lead"
        ),
        debate_choices,
    )
    workflow.add_conditional_edges(
        "Downside Case",
        lambda s: _route_debate(
            s, RESEARCH_DEBATE_PARTICIPANTS, "research_debate", "Investment Lead"
        ),
        debate_choices,
    )
    workflow.add_edge("Investment Lead", "Trader")
    workflow.add_edge("Trader", END)

    return workflow
