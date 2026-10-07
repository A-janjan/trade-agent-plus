"""Run the pipeline from the command line:

    python -m tradeagents TICKER YYYY-MM-DD [options]

Options:
    --analysts=a,b,c    Select analysts (default: all four)
    --no-display        Suppress the live progress display
    --debug             Use the verbose debug path
"""

from __future__ import annotations

import sys

from tradeagents.default_config import DEFAULT_CONFIG
from tradeagents.graph import TradingGraph
from tradeagents.graph.progress import ProgressDisplay
from tradeagents.observability import flush as flush_traces

_ALL = ("market", "social", "news", "fundamentals")
_REPORT_KEYS = (
    "market_report",
    "sentiment_report",
    "news_report",
    "fundamentals_report",
)


def _parse_args(argv: list[str]) -> tuple[str, str, tuple[str, ...], bool, bool]:
    flags = {a for a in argv if a.startswith("--")}
    positional = [a for a in argv if not a.startswith("--")]

    analysts = _ALL
    for a in argv:
        if a.startswith("--analysts="):
            analysts = tuple(a.split("=", 1)[1].split(","))

    if len(positional) < 2:
        print(__doc__)
        raise SystemExit(1)

    return (
        positional[0],
        positional[1],
        analysts,
        "--debug" in flags,
        "--no-display" not in flags,
    )


def main() -> int:
    ticker, trade_date, analysts, debug, want_display = _parse_args(sys.argv[1:])

    graph = TradingGraph(
        selected_analysts=analysts,
        config=DEFAULT_CONFIG.copy(),
        debug=debug,
    )

    display = None
    if want_display:
        display = ProgressDisplay(title=f"tradeagents · {ticker} · {trade_date}")

    try:
        final, plan = graph.propagate(ticker, trade_date, display=display)
    finally:
        # A process that exits before the SDK's batch drains loses its trace;
        # flushing in a finally means a failed run is traced too.
        flush_traces()

    for key in _REPORT_KEYS:
        report = final.get(key, "")
        if report:
            print(f"\n===== {key} =====\n\n{report}")
    if plan:
        print(f"\n===== investment_plan =====\n\n{plan}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
