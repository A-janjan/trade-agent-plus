"""Top-level orchestration: build the graph, create a run's initial state, run it."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, cast

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from tradeagents.agents.context import build_instrument_context
from tradeagents.agents.state import AgentState, InvestDebateState, RiskDebateState
from tradeagents.dataflows.date_window import get_current_date
from tradeagents.default_config import DEFAULT_CONFIG
from tradeagents.graph.setup import build_graph
from tradeagents.llm_clients import create_llm
from tradeagents.portfolio import PortfolioContext

logger = logging.getLogger(__name__)


def _validate_trade_date(value: Any) -> str:
    """The run date as a canonical YYYY-MM-DD string no later than today."""
    text = str(value)
    try:
        parsed = datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        raise ValueError(
            f"trade_date must be a date in YYYY-MM-DD format, got {value!r}"
        ) from None
    canonical = parsed.strftime("%Y-%m-%d")
    if canonical != text:
        raise ValueError(f"trade_date must be canonical YYYY-MM-DD, got {value!r}")
    if text > get_current_date():
        raise ValueError(f"trade_date cannot be in the future: {text}")
    return text


class TradingGraph:
    """The analyst graph and its run entry point."""

    def __init__(
        self,
        selected_analysts: tuple[str, ...] = ("market",),
        config: dict | None = None,
        debug: bool = False,
    ):
        self.config = config or DEFAULT_CONFIG.copy()
        self.selected_analysts = tuple(selected_analysts)
        self.debug = debug

        self.quick_llm = create_llm(self.config, "quick")
        # The deep LLM is not needed until future Phases; build it lazily so a
        # run needs only the quick model's key.
        self._deep_llm = None

        self.workflow = build_graph(
            self.selected_analysts, self.quick_llm, self._deep_llm
        )
        self.graph = self.workflow.compile()

    def propagate(
        self,
        ticker: str,
        trade_date: str,
        asset_type: str = "stock",
        portfolio: PortfolioContext | None = None,
    ) -> tuple[dict, str]:
        """Run the analyst graph once.

        Returns ``(final_state, market_report)``. The market report is also
        available as ``final_state["market_report"]``; the tuple is convenience.
        """
        trade_date = _validate_trade_date(trade_date)
        state = self._initial_state(ticker, trade_date, asset_type, portfolio)
        cfg = cast(
            RunnableConfig,
            {"recursion_limit": self.config["max_recur_limit"]},
        )

        if self.debug:
            final: dict[str, Any] = dict(state)
            for step in self.graph.stream(state, config=cfg, stream_mode="values"):
                if isinstance(step, dict):
                    final = step
            return final, final.get("market_report", "")

        final: dict[str, Any] = self.graph.invoke(state, config=cfg)
        return final, final.get("market_report", "")

    def _initial_state(
        self,
        ticker: str,
        trade_date: str,
        asset_type: str,
        portfolio: PortfolioContext | None,
    ) -> AgentState:
        """Assemble the run's initial state.

        Every field ``AgentState`` declares is present, even ones no selected
        analyst touches, so later phases can start reading them without
        re-plumbing this function.
        """
        return {
            "messages": [HumanMessage(content=f"Analyze {ticker} as of {trade_date}.")],
            "company_of_interest": ticker,
            "asset_type": asset_type,
            "trade_date": trade_date,
            "instrument_context": build_instrument_context(
                ticker, asset_type, trade_date
            ),
            "portfolio_context": (
                portfolio.render(ticker) if portfolio is not None else ""
            ),
            "past_context": "",
            "sender": "",
            "market_report": "",
            "sentiment_report": "",
            "news_report": "",
            "fundamentals_report": "",
            "investment_debate_state": InvestDebateState(
                {
                    "bull_history": "",
                    "bear_history": "",
                    "history": "",
                    "current_response": "",
                    "judge_decision": "",
                    "count": 0,
                }
            ),
            "investment_plan": "",
            "trader_investment_plan": "",
            "risk_debate_state": RiskDebateState(
                {
                    "aggressive_history": "",
                    "conservative_history": "",
                    "neutral_history": "",
                    "history": "",
                    "latest_speaker": "",
                    "current_aggressive_response": "",
                    "current_conservative_response": "",
                    "current_neutral_response": "",
                    "judge_decision": "",
                    "count": 0,
                }
            ),
            "final_trade_decision": "",
        }
