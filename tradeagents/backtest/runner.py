"""Execute a backtest: one graph run per (ticker, date) cell, into a run-local log.

The live decision log is never touched. A sweep would otherwise flood the
context that real runs read back through the PM's ``past_context`` — a
100-cell sweep for NVDA would bury every other ticker's lessons under NVDA
entries.

Cells are independent. The portfolio, when given, is the same standing book
for every cell rather than a position carried forward, because carrying a
position forward would require a fill model this system does not have. That
is a scope decision, not a limitation to be worked around.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from tradeagents.dataflows.symbols import safe_ticker_component
from tradeagents.graph.trading_graph import TradingGraph
from tradeagents.portfolio import PortfolioContext

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """What a sweep produced: where its log lives and what happened while it ran."""

    run_id: str
    run_dir: Path
    log_path: Path
    cells_run: int = 0
    cells_skipped: int = 0
    cell_failures: list[tuple[str, str, str]] = field(default_factory=list)
    settlement_failures: list[tuple[str, str]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.cell_failures and not self.settlement_failures


def _default_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def run_backtest(
    tickers: list[str],
    dates: list[str],
    config: dict[str, Any],
    *,
    asset_type: str = "stock",
    portfolio: PortfolioContext | None = None,
    selected_analysts: tuple[str, ...] = ("market", "social", "news", "fundamentals"),
    run_id: str | None = None,
) -> BacktestResult:
    """Analyze every ticker on every date, into a decision log of this run's own.

    Returns a :class:`BacktestResult` describing what ran and what it wrote.
    Per-cell exceptions are collected rather than raised: one unreachable
    vendor on one cell must not end a sweep of hundreds.
    """
    # run_id becomes a path segment; validate it the same way a ticker is
    # validated so a stray "../" cannot place the run outside results_dir.
    run_id = safe_ticker_component(run_id or _default_run_id())

    run_dir = Path(config["results_dir"]) / "backtest" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    run_config = {
        **config,
        "results_dir": str(run_dir),
        "memory_log_path": str(run_dir / "decisions.jsonl"),
        # A sweep is long and repetitive; a checkpoint is pointless (each cell
        # is a fresh graph call) and would leave per-ticker DBs to clean up.
        "checkpoint_enabled": False,
    }

    graph = TradingGraph(selected_analysts, config=run_config)
    result = BacktestResult(
        run_id=run_id,
        run_dir=run_dir,
        log_path=Path(run_config["memory_log_path"]),
    )

    # Cells already in this run's log are skipped, so an interrupted sweep
    # resumes by being launched again with the same run_id.
    done = {(e["ticker"], e["trade_date"]) for e in graph.log.all_entries()}

    for ticker in tickers:
        for date in dates:
            if (ticker, date) in done:
                result.cells_skipped += 1
                continue
            try:
                graph.propagate(
                    ticker, date, asset_type=asset_type, portfolio=portfolio
                )
                result.cells_run += 1
                logger.info("Cell ok: %s %s", ticker, date)
            except (
                Exception
            ) as exc:  # noqa: BLE001 — one bad cell must not end the sweep
                logger.warning("Cell failed: %s %s — %s", ticker, date, exc)
                result.cell_failures.append((ticker, date, str(exc)))

    # Settlement runs on the way into a run, which resolves a ticker's earlier
    # cells but never its last. One closing pass per ticker closes that gap so
    # the final cell of each ticker can be scored on the next read.
    for ticker in tickers:
        try:
            graph._settle(ticker)
        except Exception as exc:  # noqa: BLE001 — reflection calls a provider
            logger.warning("Closing settlement failed for %s: %s", ticker, exc)
            result.settlement_failures.append((ticker, str(exc)))

    return result
