from __future__ import annotations

import pytest

from tradeagents.memory.context import build_past_context
from tradeagents.memory.log import DecisionLog


@pytest.fixture
def log(tmp_path):
    return DecisionLog(tmp_path / "log.jsonl")


def _settle(log, ticker, date, raw, alpha, reflection, resolved="2026-09-08"):
    log.record(
        {
            "ticker": ticker,
            "trade_date": date,
            "rating": "Buy",
            "decision": f"Decision for {ticker} {date}.",
        }
    )
    log.settle(
        ticker,
        date,
        raw_return=raw,
        alpha_return=alpha,
        holding_days=5,
        resolved_date=resolved,
        benchmark="SPY",
        reflection=reflection,
    )


@pytest.mark.unit
def test_empty_log_returns_empty_string(log):
    assert build_past_context(log, "NVDA") == ""


@pytest.mark.unit
def test_only_pending_returns_empty(log):
    log.record(
        {
            "ticker": "NVDA",
            "trade_date": "2026-09-01",
            "rating": "Buy",
            "decision": "Buy.",
        }
    )
    assert build_past_context(log, "NVDA") == ""


@pytest.mark.unit
def test_same_ticker_shows_full_entry(log):
    _settle(log, "NVDA", "2026-08-01", 0.02, 0.01, "Lesson A.")
    text = build_past_context(log, "NVDA")
    assert "Past decisions on NVDA" in text
    assert "Lesson A." in text
    assert "Decision for NVDA 2026-08-01" in text


@pytest.mark.unit
def test_cross_ticker_shows_reflection_only(log):
    _settle(log, "AAPL", "2026-08-01", 0.02, 0.01, "Apple lesson.")
    text = build_past_context(log, "NVDA")
    assert "Recent cross-ticker lessons" in text
    assert "Apple lesson." in text
    # The full decision does not appear for cross-ticker entries.
    assert "Decision for AAPL" not in text


@pytest.mark.unit
def test_as_of_filters_outcomes_not_yet_known(log):
    _settle(log, "NVDA", "2026-08-01", 0.02, 0.01, "Old lesson.", resolved="2026-08-08")
    _settle(
        log, "NVDA", "2026-09-15", 0.03, 0.02, "Future lesson.", resolved="2026-09-22"
    )
    # A run dated before the second outcome was known sees only the first.
    text = build_past_context(log, "NVDA", as_of="2026-09-01")
    assert "Old lesson." in text
    assert "Future lesson." not in text


@pytest.mark.unit
def test_caps_same_and_cross_counts(log):
    for i, t in enumerate(
        [
            "2026-08-01",
            "2026-08-08",
            "2026-08-15",
            "2026-08-22",
            "2026-08-29",
            "2026-09-05",
        ]
    ):
        _settle(log, "NVDA", t, 0.01, 0.005, f"Same {i}", resolved="2026-09-15")
    for t in ["2026-08-01", "2026-08-08", "2026-08-15", "2026-08-22"]:
        _settle(log, "AAPL", t, 0.01, 0.005, f"Cross {t}", resolved="2026-09-15")

    text = build_past_context(log, "NVDA", n_same=2, n_cross=1)
    assert text.count("Same") == 2
    assert text.count("Cross") == 1
