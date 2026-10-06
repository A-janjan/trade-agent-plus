"""The graph state.

``AgentState`` extends LangGraph's ``MessagesState`` and adds every field the
pipeline reads or writes. Debate state is one generic shape (a transcript plus
a round limit and a verdict) reused by both debates — the research debate
between two participants and the risk debate between three.
"""

from __future__ import annotations

from typing import Annotated, TypedDict

from langgraph.graph import MessagesState


class DebateTurn(TypedDict):
    """One contribution to a debate."""

    speaker: str
    content: str


class DebateState(TypedDict):
    """A fixed-length debate between an ordered list of participants.

    ``transcript`` holds every turn in order; the participant who speaks next
    is determined by the transcript's length and last speaker, so no separate
    counter is needed. ``verdict`` is filled by the judge when the debate
    concludes.
    """

    transcript: list[DebateTurn]
    max_rounds: int
    verdict: str


class AgentState(MessagesState):
    """Top-level graph state."""

    # Run inputs
    company_of_interest: Annotated[str, "Ticker symbol under analysis"]
    asset_type: Annotated[str, "stock or crypto"]
    trade_date: Annotated[str, "Analysis date, YYYY-MM-DD"]
    instrument_context: Annotated[str, "Ticker identity resolved at run start"]
    portfolio_context: Annotated[str, "Caller portfolio rendered at run start"]
    past_context: Annotated[str, "Memory-log lessons injected at run start"]

    # Bookkeeping
    sender: Annotated[str, "Agent that emitted the latest message"]

    # Analyst reports
    market_report: Annotated[str, "Market Analyst report"]
    sentiment_report: Annotated[str, "Sentiment Analyst report"]
    news_report: Annotated[str, "News Analyst report"]
    fundamentals_report: Annotated[str, "Fundamentals Analyst report"]

    # Research debate
    research_debate: Annotated[DebateState, "Two-sided investment debate"]
    investment_plan: Annotated[str, "Investment Lead's synthesized plan"]

    # Trader
    trader_investment_plan: Annotated[str, "Trader's transaction proposal"]

    # Risk debate
    risk_debate: Annotated[DebateState, "Three-sided risk debate"]
    final_trade_decision: Annotated[str, "Portfolio Manager's final decision"]
