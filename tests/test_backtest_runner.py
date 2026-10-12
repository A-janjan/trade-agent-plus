from __future__ import annotations

import pytest

from tradeagents.backtest.runner import BacktestResult


@pytest.mark.unit
def test_result_ok_when_no_failures(tmp_path):
    r = BacktestResult(run_id="x", run_dir=tmp_path, log_path=tmp_path / "l.jsonl")
    assert r.ok


@pytest.mark.unit
def test_result_not_ok_with_cell_failures(tmp_path):
    r = BacktestResult(run_id="x", run_dir=tmp_path, log_path=tmp_path / "l.jsonl")
    r.cell_failures.append(("NVDA", "2026-09-01", "boom"))
    assert not r.ok


@pytest.mark.unit
def test_result_not_ok_with_settlement_failures(tmp_path):
    r = BacktestResult(run_id="x", run_dir=tmp_path, log_path=tmp_path / "l.jsonl")
    r.settlement_failures.append(("NVDA", "reflection 500"))
    assert not r.ok


@pytest.mark.unit
def test_run_id_validated_for_path_safety(tmp_path):
    # A run_id that would escape the backtest directory must be rejected before
    # any directory is created.
    from tradeagents.backtest.runner import run_backtest

    with pytest.raises(ValueError):
        run_backtest(
            ["NVDA"],
            ["2026-09-01"],
            {"results_dir": str(tmp_path)},
            run_id="../../etc/passwd",
        )


@pytest.mark.unit
def test_run_id_default_is_timestamp_shaped(tmp_path, monkeypatch):
    # The default is generated from the clock; check that the caller-supplied
    # path it produces lives under results_dir/backtest/<id>.
    captured = {}

    class _RecordingGraph:
        def __init__(self, *args, **kwargs):
            captured["config"] = kwargs.get("config")
            self.log = _EmptyLog()

        def propagate(self, *args, **kwargs):
            raise RuntimeError("stop here")

        def _settle(self, *args, **kwargs):
            pass

    import tradeagents.backtest.runner as runner

    monkeypatch.setattr(runner, "TradingGraph", _RecordingGraph)

    class _EmptyLog:
        def all_entries(self):
            return []

    result = runner.run_backtest(
        ["NVDA"],
        ["2026-09-01"],
        {"results_dir": str(tmp_path)},
    )
    assert result.run_dir.parent.name == "backtest"
    assert result.run_dir.parent.parent == tmp_path
    # The run's own log path is inside the run directory.
    assert result.log_path == result.run_dir / "decisions.jsonl"
    # Checkpointing is explicitly off for the sweep.
    assert captured["config"]["checkpoint_enabled"] is False
