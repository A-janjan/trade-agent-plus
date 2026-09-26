"""The graph state.

``AgentState`` extends LangGraph's ``MessagesState`` (which provides the
``messages`` channel with the append reducer already wired) and adds every
field the analysts, researchers, trader, and risk debate will read or write.
Fields are declared now so downstream phases only fill them in.
"""

from __future__ import annotations

from typing import Annotated, TypedDict

from langgraph.graph import MessagesState


class InvestDebateState(TypedDict):
    """Bull/bear debate state, populated during the research phase."""

    bull_history: Annotated[str, "Bull argument history"]
    bear_history: Annotated[str, "Bear argument history"]
    history: Annotated[str, "Full debate transcript"]
    current_response: Annotated[str, "Most recent argument"]
    judge_decision: Annotated[str, "Research Manager's plan"]
    count: Annotated[int, "Turns spoken so far"]


class RiskDebateState(TypedDict):
    """Three-way risk debate state, populated before the final decision."""

    aggressive_history: Annotated[str, "Aggressive analyst history"]
    conservative_history: Annotated[str, "Conservative analyst history"]
    neutral_history: Annotated[str, "Neutral analyst history"]
    history: Annotated[str, "Full debate transcript"]
    latest_speaker: Annotated[str, "Who spoke last"]
    current_aggressive_response: Annotated[str, "Latest aggressive argument"]
    current_conservative_response: Annotated[str, "Latest conservative argument"]
    current_neutral_response: Annotated[str, "Latest neutral argument"]
    judge_decision: Annotated[str, "Portfolio Manager's decision"]
    count: Annotated[int, "Turns spoken so far"]


class AgentState(MessagesState):
    """Top-level graph state."""

    # Run inputs
    company_of_interest: Annotated[str, "Ticker symbol under analysis"]
    asset_type: Annotated[str, "stock or crypto"]
    trade_date: Annotated[str, "Analysis date, YYYY-MM-DD"]
    instrument_context: Annotated[
        str, "Deterministic ticker identity resolved at run start"
    ]
    portfolio_context: Annotated[
        str, "Caller portfolio rendered at run start; empty when absent"
    ]
    past_context: Annotated[str, "Memory-log lessons injected at run start"]

    # Bookkeeping
    sender: Annotated[str, "Agent that emitted the latest message"]

    # Analyst reports
    market_report: Annotated[str, "Market Analyst report"]
    sentiment_report: Annotated[str, "Sentiment Analyst report"]
    news_report: Annotated[str, "News Analyst report"]
    fundamentals_report: Annotated[str, "Fundamentals Analyst report"]

    # Research phase
    investment_debate_state: Annotated[InvestDebateState, "Bull/bear debate state"]
    investment_plan: Annotated[str, "Research Manager's investment plan"]

    # Trader
    trader_investment_plan: Annotated[str, "Trader's transaction proposal"]

    # Risk phase
    risk_debate_state: Annotated[RiskDebateState, "Risk debate state"]
    final_trade_decision: Annotated[str, "Portfolio Manager's final decision"]
