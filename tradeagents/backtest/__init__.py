"""Backtesting: run the pipeline over a grid and score the outcomes.

The decision log is the results table. A cell's run records its decision; a
later run's settlement resolves it with realized return and alpha. Scoring
reads what the log already contains — there is no parallel record to keep in
sync with reality.

Scope is decision quality, not portfolio simulation. Turning a rating into a
filled order needs a quantity, a fill price, and a cash ledger, none of which
this system has. Inventing them here would put an execution model behind an
evaluation tool. Cells are independent; the portfolio, when one is given, is
the same standing book for every cell.
"""

from __future__ import annotations

from tradeagents.backtest.grid import iter_grid
from tradeagents.backtest.runner import BacktestResult, run_backtest
from tradeagents.backtest.scoring import BacktestSummary, RatingScore, summarize

__all__ = [
    "BacktestResult",
    "BacktestSummary",
    "RatingScore",
    "iter_grid",
    "run_backtest",
    "summarize",
]
