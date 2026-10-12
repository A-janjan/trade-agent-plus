"""Top-level orchestration: build the graph, create a run's initial state, run it."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from tradeagents.agents.context import build_instrument_context
from tradeagents.agents.state import AgentState
from tradeagents.dataflows.date_window import get_current_date
from tradeagents.dataflows.symbols import safe_ticker_component
from tradeagents.default_config import DEFAULT_CONFIG
from tradeagents.graph.progress import ProgressDisplay, stream_graph
from tradeagents.graph.setup import build_graph
from tradeagents.llm_clients import create_llm
from tradeagents.memory.context import build_past_context
from tradeagents.memory.log import DecisionLog
from tradeagents.memory.rating import parse_rating
from tradeagents.memory.settlement import settle_pending
from tradeagents.observability import build_callbacks, trace_metadata
from tradeagents.portfolio import PortfolioContext
from tradeagents.reporting import write_report_tree

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
        self.log = DecisionLog(self.config["memory_log_path"])
        self.selected_analysts = tuple(selected_analysts)
        self.debug = debug

        # Streaming is what makes a live display possible; the display turns it
        # on, and a config key can turn it on for a headless run too.
        streaming = bool(self.config.get("streaming"))
        self.quick_llm = create_llm(self.config, "quick", streaming=streaming)
        self.deep_llm = create_llm(self.config, "deep", streaming=streaming)

        self.workflow = build_graph(
            self.selected_analysts, self.quick_llm, self.deep_llm
        )
        self.graph = self.workflow.compile()

    def build_run_config(
        self,
        ticker: str,
        trade_date: str,
        *,
        asset_type: str = "stock",
        trace_session: str | None = None,
    ) -> RunnableConfig:
        """The RunnableConfig for one run: recursion limit, callbacks, trace metadata.

        Langfuse reads its own keys out of ``metadata`` (``langfuse_session_id``,
        ``langfuse_tags``) and the trace's display name out of ``run_name``; the
        rest is plain metadata visible on the trace. Passing all of it here
        rather than at the call site keeps the wiring in one place.
        """
        meta = trace_metadata(
            ticker,
            trade_date,
            asset_type=asset_type,
            session_id=trace_session or ticker.upper(),
        )
        return cast(
            RunnableConfig,
            {
                "recursion_limit": self.config["max_recur_limit"],
                "callbacks": build_callbacks(self.config),
                "run_name": meta.pop("run_name"),
                "metadata": meta,
            },
        )

    def propagate(
        self,
        ticker: str,
        trade_date: str,
        asset_type: str = "stock",
        portfolio: PortfolioContext | None = None,
        display: ProgressDisplay | None = None,
    ) -> tuple[dict, str]:
        """Run the pipeline once.

        Returns ``(final_state, primary_output)``, where ``primary_output`` is
        the Portfolio Manager's final decision. If any prior decisions for this
        ticker were settled on the way in, they are attached to
        ``final_state["settled"]`` so the caller can tell the user what it
        learned.
        """
        trade_date = _validate_trade_date(trade_date)
        settled = self._settle(ticker)
        state = self._initial_state(ticker, trade_date, asset_type, portfolio)

        if display is not None and not self.config.get("streaming"):
            # Rebuild the models with streaming on; the graph holds references
            # to the old ones, so the whole graph is rebuilt rather than
            # reached into. Cheap next to the run it enables.
            self.config = {**self.config, "streaming": True}
            self.quick_llm = create_llm(self.config, "quick", streaming=True)
            self.deep_llm = create_llm(self.config, "deep", streaming=True)
            self.workflow = build_graph(
                self.selected_analysts, self.quick_llm, self.deep_llm
            )
            self.graph = self.workflow.compile()

        cfg = self.build_run_config(ticker, trade_date, asset_type=asset_type)

        if display is not None:
            final = stream_graph(self.graph, state, cast(dict, cfg), display)
        else:
            final = self.graph.invoke(state, config=cfg)

        final["settled"] = settled
        self.record_decision(ticker, trade_date, final)
        return final, final.get("final_trade_decision", "")

    def _settle(self, ticker):
        """Settle prior decisions for this ticker. Never raises on failure.

        A reflection call goes to a provider, and this runs on the way into a
        new run: a transient failure leaves the entry pending rather than
        aborting the analysis the user actually asked for.
        """
        try:
            return settle_pending(ticker, self.log, self.quick_llm, self.config)
        except Exception as exc:
            logger.warning("Settlement failed for %s: %s", ticker, exc)
            return []

    def _memory_as_of(self, trade_date: str) -> str | None:
        """The point-in-time cutoff for past lessons.

        A historical run (trade date before today) sees only lessons whose
        outcome was already known by the trade date — a backtest must not learn
        from an outcome that had not happened yet. A live run sees everything
        settled, since the entry's own resolution date is already behind it.
        """
        return trade_date if trade_date < get_current_date() else None

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
            "past_context": build_past_context(
                self.log,
                ticker,
                as_of=self._memory_as_of(trade_date),
            ),
            "sender": "",
            "market_report": "",
            "sentiment_report": "",
            "news_report": "",
            "fundamentals_report": "",
            "research_debate": {
                "transcript": [],
                "max_rounds": self.config["max_debate_rounds"],
                "verdict": "",
            },
            "risk_debate": {
                "transcript": [],
                "max_rounds": self.config["max_risk_discuss_rounds"],
                "verdict": "",
            },
            "investment_plan": "",
            "trader_investment_plan": "",
            "final_trade_decision": "",
            "final_rating": "",
        }

    def record_decision(self, ticker, trade_date, final_state) -> bool:
        """Persist the run's decision to the log. Returns whether it was recorded.

        A re-run of the same ticker and date is a no-op: recording it twice
        would double-count the decision in every aggregate over the log.
        """
        decision = final_state.get("final_trade_decision")
        if not decision:
            logger.warning(
                "No final decision for %s on %s; nothing logged", ticker, trade_date
            )
            return False

        # Prefer the PM's structured rating; fall back to parsing the rendered
        # markdown only when the structured path did not run.
        rating = final_state.get("final_rating") or parse_rating(decision)

        return self.log.record(
            {
                "ticker": ticker,
                "trade_date": trade_date,
                "rating": rating,
                "decision": decision,
            }
        )

    def save_reports(
        self,
        final_state: dict,
        ticker: str,
        save_path: str | Path | None = None,
    ) -> Path:
        """Write the run's report tree to disk; return the complete-report path.

        When ``save_path`` is not given, a timestamped directory under
        ``results_dir`` is used, so a headless run gets the same on-disk
        artifact the CLI does without the caller naming a location.

        ``settled`` and ``past_context`` come off ``final_state`` — the graph
        already attached them — so the report reflects what the run knew and
        learned, not just what it decided.
        """
        if save_path is None:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = (
                Path(self.config["results_dir"])
                / "reports"
                / f"{safe_ticker_component(ticker)}_{stamp}"
            )
        return write_report_tree(
            final_state,
            ticker,
            save_path,
            config=self.config,
            settled=final_state.get("settled") or [],
            past_context=final_state.get("past_context") or "",
        )
