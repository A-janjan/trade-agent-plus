"""Run the pipeline from the command line:

    python -m tradeagents TICKER YYYY-MM-DD [options]

Options:
    --analysts=a,b,c    Select analysts (default: all four)
    --no-display        Suppress the live progress display
    --save[=PATH]       Write the report tree; default is a timestamped
                        directory under results_dir
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


def _parse_args(
    argv: list[str],
) -> tuple[str, str, tuple[str, ...], bool, bool, str | None]:
    flags = {a for a in argv if a.startswith("--")}
    positional = [a for a in argv if not a.startswith("--")]

    analysts = _ALL
    save_path: str | None = None
    for a in argv:
        if a.startswith("--analysts="):
            analysts = tuple(a.split("=", 1)[1].split(","))
        elif a == "--save":
            save_path = ""  # sentinel: caller wants saving, default path
        elif a.startswith("--save="):
            save_path = a.split("=", 1)[1]

    if len(positional) < 2:
        print(__doc__)
        raise SystemExit(1)

    return (
        positional[0],
        positional[1],
        analysts,
        "--debug" in flags,
        "--no-display" not in flags,
        save_path,
    )


def main() -> int:
    ticker, trade_date, analysts, debug, want_display, save = _parse_args(sys.argv[1:])

    graph = TradingGraph(
        selected_analysts=analysts,
        config=DEFAULT_CONFIG.copy(),
        debug=debug,
    )

    display = None
    if want_display:
        display = ProgressDisplay(title=f"tradeagents · {ticker} · {trade_date}")

    try:
        final, _ = graph.propagate(ticker, trade_date, display=display)
    finally:
        flush_traces()

    # Settled prior decisions came back on the state; report what was learned
    # before printing the current run's output.
    settled = final.get("settled") or []
    if settled:
        print(f"\nSettled {len(settled)} prior decision(s) for {ticker}:")
        for e in settled:
            print(
                f"  - {e['trade_date']}: {e['rating']} | "
                f"{e['raw_return']:+.1%} raw | {e['alpha_return']:+.1%} alpha vs "
                f"{e['benchmark']} | {e['holding_days']}d"
            )

    if save is not None:
        path = graph.save_reports(final, ticker, save_path=save or None)
        print(f"\nReports written to {path}")

    for key in _REPORT_KEYS:
        report = final.get(key, "")
        if report:
            print(f"\n===== {key} =====\n\n{report}")
    for key in ("investment_plan", "trader_investment_plan", "final_trade_decision"):
        text = final.get(key, "")
        if text:
            print(f"\n===== {key} =====\n\n{text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
