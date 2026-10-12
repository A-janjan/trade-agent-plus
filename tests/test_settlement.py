from __future__ import annotations

import pandas as pd
import pytest

from tradeagents.memory import settlement

# ---- resolve_benchmark ----


@pytest.mark.unit
def test_benchmark_explicit_override_wins():
    config = {"benchmark_ticker": "QQQ", "benchmark_map": {".T": "^N225", "": "SPY"}}
    assert settlement.resolve_benchmark("7203.T", config) == "QQQ"


@pytest.mark.unit
def test_benchmark_by_suffix():
    config = {
        "benchmark_ticker": None,
        "benchmark_map": {".T": "^N225", ".L": "^FTSE", "": "SPY"},
    }
    assert settlement.resolve_benchmark("7203.T", config) == "^N225"
    assert settlement.resolve_benchmark("AZN.L", config) == "^FTSE"


@pytest.mark.unit
def test_benchmark_falls_through_to_default():
    config = {"benchmark_ticker": None, "benchmark_map": {"": "SPY"}}
    assert settlement.resolve_benchmark("AAPL", config) == "SPY"
    # A dotted US ticker with no matching suffix also falls through.
    assert settlement.resolve_benchmark("BRK.B", config) == "SPY"


@pytest.mark.unit
def test_benchmark_canonicalizes_explicit_alias():
    config = {"benchmark_ticker": "spx500", "benchmark_map": {"": "SPY"}}
    # normalize_symbol maps SPX500 -> ^GSPC.
    assert settlement.resolve_benchmark("AAPL", config) == "^GSPC"


# ---- fetch_outcome ----


@pytest.fixture
def stub_closes(monkeypatch):
    """Replace get_closes with a scripted series."""

    def _install(stock_values, bench_values):
        def fake_get_closes(symbol, start, end):
            values = stock_values if symbol == "NVDA" else bench_values
            return pd.Series(
                values,
                index=pd.date_range("2026-09-01", periods=len(values), freq="B"),
            )

        monkeypatch.setattr(settlement, "get_closes", fake_get_closes)

    return _install


@pytest.mark.unit
def test_fetch_outcome_returns_full_window_result(stub_closes):
    stub_closes(
        stock_values=[100.0, 101.0, 102.0, 103.0, 104.0, 105.0],
        bench_values=[400.0, 401.0, 402.0, 403.0, 404.0, 405.0],
    )
    result = settlement.fetch_outcome(
        "NVDA", "2026-09-01", holding_days=5, benchmark="SPY"
    )
    assert result is not None
    assert result["raw_return"] == pytest.approx(0.05)
    assert result["alpha_return"] == pytest.approx(0.05 - 0.0125)
    assert result["holding_days"] == 5
    assert result["benchmark"] == "SPY"


@pytest.mark.unit
def test_fetch_outcome_returns_none_when_window_incomplete(stub_closes):
    stub_closes(
        stock_values=[100.0, 101.0, 102.0],  # only 2 trading days past start
        bench_values=[400.0, 401.0, 402.0],
    )
    result = settlement.fetch_outcome(
        "NVDA", "2026-09-01", holding_days=5, benchmark="SPY"
    )
    assert result is None


@pytest.mark.unit
def test_fetch_outcome_returns_none_on_exception(monkeypatch):
    def boom(*_a, **_kw):
        raise RuntimeError("network down")

    monkeypatch.setattr(settlement, "get_closes", boom)
    result = settlement.fetch_outcome(
        "NVDA", "2026-09-01", holding_days=5, benchmark="SPY"
    )
    assert result is None


# ---- settle_pending ----


class ScriptedLLM:
    def __init__(self, responses):
        self._responses = list(responses)
        self._i = 0

    def invoke(self, messages):
        r = self._responses[self._i]
        self._i += 1
        return r


@pytest.mark.unit
def test_settle_pending_with_no_pending_returns_empty(tmp_path):
    from tradeagents.memory.log import DecisionLog

    log = DecisionLog(tmp_path / "log.jsonl")
    result = settlement.settle_pending(
        "NVDA",
        log,
        ScriptedLLM([]),
        {
            "holding_period_days": 5,
            "benchmark_ticker": None,
            "benchmark_map": {"": "SPY"},
        },
    )
    assert result == []


@pytest.mark.unit
def test_settle_pending_skips_entry_when_window_not_traded(tmp_path, stub_closes):
    from tradeagents.memory.log import DecisionLog

    log = DecisionLog(tmp_path / "log.jsonl")
    log.record(
        {
            "ticker": "NVDA",
            "trade_date": "2026-09-01",
            "rating": "Buy",
            "decision": "Buy.",
        }
    )
    stub_closes(stock_values=[100.0, 101.0], bench_values=[400.0, 401.0])
    settled = settlement.settle_pending(
        "NVDA",
        log,
        ScriptedLLM([]),
        {
            "holding_period_days": 5,
            "benchmark_ticker": None,
            "benchmark_map": {"": "SPY"},
        },
    )
    assert settled == []
    # Still pending, will retry next run.
    assert not log.all_entries()[0].get("settled")


@pytest.mark.unit
def test_settle_pending_survives_llm_failure(tmp_path, stub_closes):
    from tradeagents.memory.log import DecisionLog

    class FailingLLM:
        def invoke(self, messages):
            raise RuntimeError("provider 500")

    log = DecisionLog(tmp_path / "log.jsonl")
    log.record(
        {
            "ticker": "NVDA",
            "trade_date": "2026-09-01",
            "rating": "Buy",
            "decision": "Buy.",
        }
    )
    stub_closes(
        stock_values=[100.0, 101.0, 102.0, 103.0, 104.0, 105.0],
        bench_values=[400.0, 401.0, 402.0, 403.0, 404.0, 405.0],
    )
    settled = settlement.settle_pending(
        "NVDA",
        log,
        FailingLLM(),
        {
            "holding_period_days": 5,
            "benchmark_ticker": None,
            "benchmark_map": {"": "SPY"},
        },
    )
    assert settled == []
    # Left pending for next run.
    assert not log.all_entries()[0].get("settled")
