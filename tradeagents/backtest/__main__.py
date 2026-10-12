"""Run a backtest from the command line:

    python -m tradeagents.backtest TICKER[,TICKER...] --start YYYY-MM-DD --end YYYY-MM-DD [options]

Options:
    --every=N           Days between analysis dates (default: 7)
    --analysts=a,b,c    Select analysts (default: all four)
    --run-id=ID         Resume a previous sweep by reusing its run id
    --asset-type=T      "stock" (default) or "crypto"
    --no-summary        Skip the scoring summary
"""

from __future__ import annotations

import sys

from tradeagents.backtest.grid import iter_grid
from tradeagents.backtest.runner import run_backtest
from tradeagents.backtest.scoring import summarize
from tradeagents.default_config import DEFAULT_CONFIG

_ALL_ANALYSTS = ("market", "social", "news", "fundamentals")


_VALUE_FLAGS = {"--start", "--end", "--every", "--analysts", "--run-id", "--asset-type"}


def _normalize_argv(argv: list[str]) -> list[str]:
    """Rewrite ``--flag value`` pairs into ``--flag=value``.

    The docstring shows the space form, which is the conventional CLI spelling;
    requiring ``=`` at the parser level is a footgun users hit before anything
    else. Both forms are accepted here so the parser only ever sees one.
    """
    out: list[str] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in _VALUE_FLAGS:
            if i + 1 >= len(argv):
                raise SystemExit(f"{a} requires a value")
            out.append(f"{a}={argv[i + 1]}")
            i += 2
            continue
        out.append(a)
        i += 1
    return out


def _parse(argv: list[str]) -> dict:
    argv = _normalize_argv(argv)
    opts: dict = {
        "tickers": [],
        "start": None,
        "end": None,
        "every": 7,
        "analysts": _ALL_ANALYSTS,
        "run_id": None,
        "asset_type": "stock",
        "summary": True,
    }
    for a in argv:
        if a.startswith("--start="):
            opts["start"] = a.split("=", 1)[1]
        elif a.startswith("--end="):
            opts["end"] = a.split("=", 1)[1]
        elif a.startswith("--every="):
            opts["every"] = int(a.split("=", 1)[1])
        elif a.startswith("--analysts="):
            opts["analysts"] = tuple(a.split("=", 1)[1].split(","))
        elif a.startswith("--run-id="):
            opts["run_id"] = a.split("=", 1)[1]
        elif a.startswith("--asset-type="):
            opts["asset_type"] = a.split("=", 1)[1]
        elif a == "--no-summary":
            opts["summary"] = False
        elif not a.startswith("--"):
            opts["tickers"].extend(t.strip() for t in a.split(",") if t.strip())

    if not opts["tickers"] or not opts["start"] or not opts["end"]:
        print(__doc__)
        raise SystemExit(1)
    return opts


def main() -> int:
    opts = _parse(sys.argv[1:])
    dates = iter_grid(opts["start"], opts["end"], opts["every"])
    if not dates:
        print(f"No dates to sweep between {opts['start']} and {opts['end']}.")
        return 1

    print(
        f"Sweeping {len(opts['tickers'])} ticker(s) × {len(dates)} date(s) "
        f"= {len(opts['tickers']) * len(dates)} cells"
    )
    result = run_backtest(
        opts["tickers"],
        dates,
        DEFAULT_CONFIG.copy(),
        asset_type=opts["asset_type"],
        selected_analysts=opts["analysts"],
        run_id=opts["run_id"],
    )

    print(
        f"\nrun_id: {result.run_id}\n"
        f"run_dir: {result.run_dir}\n"
        f"cells run: {result.cells_run}, skipped: {result.cells_skipped}, "
        f"failed: {len(result.cell_failures)}"
    )
    if result.cell_failures:
        print("\nCell failures:")
        for ticker, date, err in result.cell_failures:
            print(f"  {ticker} {date}: {err}")
    if result.settlement_failures:
        print("\nSettlement failures:")
        for ticker, err in result.settlement_failures:
            print(f"  {ticker}: {err}")

    if opts["summary"]:
        print("\n" + summarize(result).render())
    return 0


if __name__ == "__main__":
    sys.exit(main())
