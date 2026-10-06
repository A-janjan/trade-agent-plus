"""Run the analyst graph from the command line:

python -m tradeagents TICKER YYYY-MM-DD [--analysts market,news] [--debug]
"""

from __future__ import annotations

import sys

from tradeagents.default_config import DEFAULT_CONFIG
from tradeagents.graph import TradingGraph

_ALL = ("market", "social", "news", "fundamentals")


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    debug = "--debug" in sys.argv
    selected = _ALL
    for a in sys.argv[1:]:
        if a.startswith("--analysts="):
            selected = tuple(a.split("=", 1)[1].split(","))

    if len(args) < 2:
        print(
            "Usage: python -m tradeagents TICKER YYYY-MM-DD "
            "[--analysts=market,social,news,fundamentals] [--debug]"
        )
        return 1

    ticker, trade_date = args[0], args[1]
    graph = TradingGraph(
        selected_analysts=selected,
        config=DEFAULT_CONFIG.copy(),
        debug=debug,
    )
    final, plan = graph.propagate(ticker, trade_date)
    for key in (
        "market_report",
        "sentiment_report",
        "news_report",
        "fundamentals_report",
    ):
        report = final.get(key, "")
        if report:
            print(f"\n===== {key} =====\n")
            print(report)
    if plan:
        print(f"\n===== investment_plan =====\n\n{plan}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
