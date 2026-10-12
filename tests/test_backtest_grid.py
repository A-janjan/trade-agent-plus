from __future__ import annotations

import pytest

from tradeagents.backtest.grid import iter_grid


@pytest.mark.unit
def test_single_day_grid():
    assert iter_grid("2026-01-05", "2026-01-05") == ["2026-01-05"]


@pytest.mark.unit
def test_step_of_one():
    dates = iter_grid("2026-01-01", "2026-01-05", every_n_days=1)
    assert dates == [
        "2026-01-01",
        "2026-01-02",
        "2026-01-03",
        "2026-01-04",
        "2026-01-05",
    ]


@pytest.mark.unit
def test_step_of_seven_lands_on_grid():
    dates = iter_grid("2026-01-01", "2026-01-29", every_n_days=7)
    assert dates == [
        "2026-01-01",
        "2026-01-08",
        "2026-01-15",
        "2026-01-22",
        "2026-01-29",
    ]


@pytest.mark.unit
def test_grid_stops_at_today():
    # A grid entirely in the past returns every requested date.
    dates = iter_grid("2020-01-01", "2020-01-03")
    assert dates == ["2020-01-01", "2020-01-02", "2020-01-03"]


@pytest.mark.unit
def test_future_grid_returns_empty():
    # No cells to sweep; the caller decides whether that is an error.
    assert iter_grid("2999-01-01", "2999-01-05") == []


@pytest.mark.unit
def test_rejects_reversed_range():
    with pytest.raises(ValueError, match="is before start"):
        iter_grid("2026-02-01", "2026-01-01")


@pytest.mark.unit
def test_rejects_bad_step():
    with pytest.raises(ValueError, match="at least 1"):
        iter_grid("2026-01-01", "2026-01-05", every_n_days=0)


@pytest.mark.unit
def test_rejects_non_canonical_date():
    with pytest.raises(ValueError, match="canonical"):
        iter_grid("2026-1-1", "2026-01-05")


@pytest.mark.unit
def test_rejects_garbage():
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        iter_grid("not a date", "2026-01-05")
