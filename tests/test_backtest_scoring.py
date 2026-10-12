from __future__ import annotations

import pytest

from tradeagents.backtest.scoring import summarize
from tradeagents.memory.log import DecisionLog


def _log(tmp_path):
    return DecisionLog(tmp_path / "log.jsonl")


def _settled(log, ticker, date, rating, raw, alpha, holding=5):
    log.record(
        {"ticker": ticker, "trade_date": date, "rating": rating, "decision": "x"}
    )
    log.settle(
        ticker,
        date,
        raw_return=raw,
        alpha_return=alpha,
        holding_days=holding,
        resolved_date="2026-09-08",
        benchmark="SPY",
        reflection="r",
    )


@pytest.mark.unit
def test_empty_log_summarizes_to_zero(tmp_path):
    log = tmp_path / "log.jsonl"
    log.touch()  # empty file, not a missing one
    s = summarize(log)
    assert s.resolved == 0
    assert s.pending == 0
    assert s.unscored == 0
    assert s.by_rating == {}


@pytest.mark.unit
def test_pending_entries_not_scored(tmp_path):
    log = _log(tmp_path)
    log.record(
        {"ticker": "NVDA", "trade_date": "2026-09-01", "rating": "Buy", "decision": "x"}
    )
    s = summarize(tmp_path / "log.jsonl")
    assert s.resolved == 0
    assert s.pending == 1


@pytest.mark.unit
def test_buy_hit_rate_counts_positive_alpha(tmp_path):
    log = _log(tmp_path)
    # 3 Buys: two with positive alpha, one negative -> hit rate 2/3.
    _settled(log, "NVDA", "2026-08-01", "Buy", 0.03, 0.02)
    _settled(log, "NVDA", "2026-08-02", "Buy", 0.02, 0.01)
    _settled(log, "NVDA", "2026-08-03", "Buy", -0.01, -0.02)
    s = summarize(tmp_path / "log.jsonl")
    buy = s.by_rating["Buy"]
    assert buy.count == 3
    assert buy.hit_rate == pytest.approx(2 / 3)
    assert buy.mean_alpha == pytest.approx((0.02 + 0.01 - 0.02) / 3)


@pytest.mark.unit
def test_sell_hit_rate_counts_negative_alpha(tmp_path):
    log = _log(tmp_path)
    _settled(log, "NVDA", "2026-08-01", "Sell", -0.03, -0.02)
    _settled(log, "NVDA", "2026-08-02", "Sell", 0.01, 0.02)  # missed
    s = summarize(tmp_path / "log.jsonl")
    sell = s.by_rating["Sell"]
    assert sell.count == 2
    assert sell.hit_rate == pytest.approx(0.5)


@pytest.mark.unit
def test_hold_has_no_hit_rate(tmp_path):
    log = _log(tmp_path)
    _settled(log, "NVDA", "2026-08-01", "Hold", 0.01, 0.00)
    s = summarize(tmp_path / "log.jsonl")
    hold = s.by_rating["Hold"]
    assert hold.count == 1
    assert hold.hit_rate is None
    assert hold.mean_alpha == pytest.approx(0.0)


@pytest.mark.unit
def test_strong_buy_and_buy_are_separate_ratings(tmp_path):
    log = _log(tmp_path)
    _settled(log, "NVDA", "2026-08-01", "Strong Buy", 0.05, 0.04)
    _settled(log, "NVDA", "2026-08-02", "Buy", 0.02, 0.01)
    s = summarize(tmp_path / "log.jsonl")
    assert set(s.by_rating) == {"Strong Buy", "Buy"}


@pytest.mark.unit
def test_holding_label_uses_entry_values(tmp_path):
    log = _log(tmp_path)
    _settled(log, "NVDA", "2026-08-01", "Buy", 0.02, 0.01, holding=5)
    s = summarize(tmp_path / "log.jsonl")
    assert s.holding == "5 trading days"


@pytest.mark.unit
def test_unscored_review_entries_counted(tmp_path):
    log = _log(tmp_path)
    log.record(
        {
            "ticker": "NVDA",
            "trade_date": "2026-08-01",
            "rating": "REVIEW",
            "decision": "x",
        }
    )
    log.settle(
        "NVDA",
        "2026-08-01",
        raw_return=0.01,
        alpha_return=0.00,
        holding_days=5,
        resolved_date="2026-09-08",
        benchmark="SPY",
        reflection="r",
    )
    s = summarize(tmp_path / "log.jsonl")
    assert s.unscored == 1
    assert s.resolved == 0


@pytest.mark.unit
def test_render_lists_ratings_in_bull_to_bear_order(tmp_path):
    log = _log(tmp_path)
    _settled(log, "NVDA", "2026-08-01", "Buy", 0.02, 0.01)
    _settled(log, "NVDA", "2026-08-02", "Sell", -0.02, -0.01)
    _settled(log, "NVDA", "2026-08-03", "Hold", 0.00, 0.00)
    text = summarize(tmp_path / "log.jsonl").render()
    assert text.index("Buy:") < text.index("Hold:") < text.index("Sell:")


@pytest.mark.unit
def test_summarize_rejects_missing_log(tmp_path):
    with pytest.raises(FileNotFoundError):
        summarize(tmp_path / "missing.jsonl")
