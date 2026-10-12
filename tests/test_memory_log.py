from __future__ import annotations

import json

import pytest

from tradeagents.memory.log import DecisionLog


@pytest.fixture
def log(tmp_path):
    return DecisionLog(tmp_path / "log.jsonl")


def _entry(**overrides):
    base = {
        "ticker": "NVDA",
        "trade_date": "2026-09-01",
        "rating": "Buy",
        "decision": "**Rating**: Buy\n\nBuy the breakout.",
    }
    base.update(overrides)
    return base


@pytest.mark.unit
def test_empty_log_reads_empty(log):
    assert log.all_entries() == []


@pytest.mark.unit
def test_record_appends_and_reads_back(log):
    assert log.record(_entry()) is True
    entries = log.all_entries()
    assert len(entries) == 1
    assert entries[0]["ticker"] == "NVDA"
    assert entries[0]["rating"] == "Buy"


@pytest.mark.unit
def test_record_rejects_duplicate_ticker_date(log):
    log.record(_entry())
    assert log.record(_entry(rating="Sell")) is False
    assert len(log.all_entries()) == 1
    # The first rating wins; a re-run does not overwrite history.
    assert log.all_entries()[0]["rating"] == "Buy"


@pytest.mark.unit
def test_record_requires_keys(log):
    with pytest.raises(ValueError, match="missing required key"):
        log.record({"ticker": "NVDA", "trade_date": "2026-09-01"})


@pytest.mark.unit
def test_has_detects_existing_entry(log):
    log.record(_entry())
    assert log.has("NVDA", "2026-09-01")
    assert not log.has("AAPL", "2026-09-01")
    assert not log.has("NVDA", "2026-09-02")


@pytest.mark.unit
def test_pending_for_returns_only_unsettled(log):
    log.record(_entry(trade_date="2026-08-01"))
    log.record(_entry(trade_date="2026-08-15"))
    log.settle(
        "NVDA",
        "2026-08-01",
        raw_return=0.02,
        alpha_return=0.01,
        holding_days=5,
        resolved_date="2026-08-08",
        benchmark="SPY",
        reflection="Lesson A.",
    )
    pending = log.pending_for("NVDA")
    assert len(pending) == 1
    assert pending[0]["trade_date"] == "2026-08-15"


@pytest.mark.unit
def test_pending_for_sorts_by_trade_date(log):
    log.record(_entry(trade_date="2026-08-15"))
    log.record(_entry(trade_date="2026-08-01"))
    pending = log.pending_for("NVDA")
    assert [p["trade_date"] for p in pending] == ["2026-08-01", "2026-08-15"]


@pytest.mark.unit
def test_settle_marks_entry_with_outcome(log):
    log.record(_entry())
    ok = log.settle(
        "NVDA",
        "2026-09-01",
        raw_return=0.034,
        alpha_return=0.012,
        holding_days=5,
        resolved_date="2026-09-08",
        benchmark="SPY",
        reflection="Direction was right.",
    )
    assert ok is True
    e = log.all_entries()[0]
    assert e["settled"] is True
    assert e["raw_return"] == 0.034
    assert e["alpha_return"] == 0.012
    assert e["reflection"] == "Direction was right."
    assert e["resolved_date"] == "2026-09-08"


@pytest.mark.unit
def test_settle_is_idempotent(log):
    log.record(_entry())
    assert (
        log.settle(
            "NVDA",
            "2026-09-01",
            raw_return=0.01,
            alpha_return=0.005,
            holding_days=5,
            resolved_date="2026-09-08",
            benchmark="SPY",
            reflection="First.",
        )
        is True
    )
    # Second call finds no pending entry and does nothing.
    assert (
        log.settle(
            "NVDA",
            "2026-09-01",
            raw_return=0.99,
            alpha_return=0.99,
            holding_days=5,
            resolved_date="2026-09-08",
            benchmark="SPY",
            reflection="Second.",
        )
        is False
    )


@pytest.mark.unit
def test_malformed_line_is_skipped(tmp_path):
    path = tmp_path / "log.jsonl"
    path.write_text(
        json.dumps(_entry())
        + "\n"
        + "not json\n"
        + json.dumps(_entry(trade_date="2026-09-02"))
        + "\n",
        encoding="utf-8",
    )
    log = DecisionLog(path)
    entries = log.all_entries()
    assert len(entries) == 2
    assert entries[0]["trade_date"] == "2026-09-01"
    assert entries[1]["trade_date"] == "2026-09-02"


@pytest.mark.unit
def test_render_markdown_shows_pending_and_settled(log):
    log.record(_entry(trade_date="2026-08-01"))
    log.record(_entry(trade_date="2026-09-01"))
    log.settle(
        "NVDA",
        "2026-08-01",
        raw_return=0.02,
        alpha_return=0.01,
        holding_days=5,
        resolved_date="2026-08-08",
        benchmark="SPY",
        reflection="Lesson A.",
    )
    text = log.render_markdown()
    assert "pending" in text
    assert "+2.0% raw" in text
    assert "Lesson A." in text
