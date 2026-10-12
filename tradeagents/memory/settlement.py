"""Settlement: score a decision once its holding window has traded.

A run settles the ticker's earlier decisions on its way in, so each run
resolves its predecessor. A decision is only settled once the full holding
window has traded — a partial return would score the call on fewer days than
it was made for, which is a different question.

An entry that cannot be settled yet (window not yet traded, symbol unreachable)
is left pending and retried next run.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from tradeagents.dataflows.symbols import normalize_symbol
from tradeagents.dataflows.vendors.yahoo.market import get_closes
from tradeagents.memory.log import DecisionLog
from tradeagents.memory.reflection import generate_reflection

logger = logging.getLogger(__name__)


def resolve_benchmark(ticker: str, config: dict) -> str:
    """The index a ticker's alpha is measured against.

    ``config["benchmark_ticker"]`` overrides everything. Otherwise the suffix
    map matches the ticker's exchange suffix (``.T`` for Tokyo, ``.L`` for
    London, and so on); US-listed tickers without a suffix get the empty-suffix
    default (``SPY`` by default). Unrecognized suffixes fall through to the
    empty-suffix entry, which is the right answer for US tickers with dots
    (``BRK.B``) that the map does not name.
    """
    explicit = config.get("benchmark_ticker")
    if explicit:
        return normalize_symbol(explicit)

    benchmark_map = config.get("benchmark_map", {})
    canonical = normalize_symbol(ticker)
    for suffix, benchmark in benchmark_map.items():
        if suffix and canonical.endswith(suffix.upper()):
            return benchmark
    return benchmark_map.get("", "SPY")


def fetch_outcome(
    ticker: str,
    trade_date: str,
    holding_days: int,
    benchmark: str,
) -> dict | None:
    """The realized return over the holding window, or None if it cannot be settled yet.

    Returns a dict with ``raw_return``, ``alpha_return``, ``holding_days``,
    ``resolved_date`` (the date of the last bar used, i.e. when the outcome
    became known), and ``benchmark``.

    None is returned when the holding window has not yet traded — a run dated
    yesterday cannot be judged five trading days later — or when either series
    is unreachable. The caller leaves the entry pending either way.
    """
    try:
        start = datetime.strptime(trade_date, "%Y-%m-%d")
        # holding_days counts trading days, so ask for the calendar span they
        # occupy (about 7 per 5), plus a week for holidays.
        end = start + timedelta(days=round(holding_days * 7 / 5) + 7)
        end_str = end.strftime("%Y-%m-%d")

        stock = get_closes(ticker, trade_date, end_str)
        bench = get_closes(benchmark, trade_date, end_str)

        # Require the full window in both series. A rerun before the window has
        # traded leaves the entry pending to retry next run, rather than
        # settling on a premature partial return.
        if len(stock) <= holding_days or len(bench) <= holding_days:
            return None

        raw = float((stock.iloc[holding_days] - stock.iloc[0]) / stock.iloc[0])
        bench_ret = float((bench.iloc[holding_days] - bench.iloc[0]) / bench.iloc[0])
        return {
            "raw_return": raw,
            "alpha_return": raw - bench_ret,
            "holding_days": holding_days,
            "resolved_date": stock.index[holding_days].strftime("%Y-%m-%d"),
            "benchmark": benchmark,
        }
    except Exception as e:
        logger.warning(
            "Could not resolve outcome for %s on %s vs %s (will retry next run): %s",
            ticker,
            trade_date,
            benchmark,
            e,
        )
        return None


def settle_pending(
    ticker: str,
    log: DecisionLog,
    llm,
    config: dict,
) -> list[dict]:
    """Settle every pending entry for ``ticker`` whose window has traded.

    Returns the settled entries (with their outcome and reflection attached), so
    the caller can tell the user what it learned rather than silently mutating
    a file. An LLM failure on one reflection leaves that entry pending for next
    run and does not stop the rest of the pass.
    """
    pending = log.pending_for(ticker)
    if not pending:
        return []

    benchmark = resolve_benchmark(ticker, config)
    holding_days = config["holding_period_days"]
    settled: list[dict] = []

    for entry in pending:
        outcome = fetch_outcome(
            entry["ticker"], entry["trade_date"], holding_days, benchmark
        )
        if outcome is None:
            continue
        try:
            reflection = generate_reflection(
                llm,
                ticker=entry["ticker"],
                trade_date=entry["trade_date"],
                decision=entry.get("decision", ""),
                raw_return=outcome["raw_return"],
                alpha_return=outcome["alpha_return"],
                holding_days=outcome["holding_days"],
                benchmark=outcome["benchmark"],
            )
        except Exception as exc:
            # The reflection call goes to a provider, and this runs on the way
            # into a new run: a transient failure leaves the entry pending
            # rather than aborting the analysis the user actually asked for.
            logger.warning(
                "Reflection failed for %s on %s: %s",
                ticker,
                entry["trade_date"],
                exc,
            )
            continue

        ok = log.settle(
            entry["ticker"],
            entry["trade_date"],
            raw_return=outcome["raw_return"],
            alpha_return=outcome["alpha_return"],
            holding_days=outcome["holding_days"],
            resolved_date=outcome["resolved_date"],
            benchmark=outcome["benchmark"],
            reflection=reflection,
        )
        if ok:
            settled.append({**entry, **outcome, "reflection": reflection})
    return settled
