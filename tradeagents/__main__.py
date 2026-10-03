"""Run the analyst graph from the command line:

python -m tradeagents TICKER YYYY-MM-DD [--debug]
"""

from __future__ import annotations

import sys

from tradeagents.default_config import DEFAULT_CONFIG
from tradeagents.graph import TradingGraph


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--debug"]
    debug = "--debug" in sys.argv

    if len(args) < 2:
        print("Usage: python -m tradeagents TICKER YYYY-MM-DD [--debug]")
        return 1

    ticker, trade_date = args[0], args[1]
    graph = TradingGraph(config=DEFAULT_CONFIG.copy(), debug=debug)
    _, report = graph.propagate(ticker, trade_date)
    print(report or "(no market report produced)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
