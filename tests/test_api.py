from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from tradeagents.api.main import create_app
from tradeagents.dataflows.config import set_config, reset_config


@pytest.fixture
def client(tmp_path):
    set_config(
        {
            "memory_log_path": str(tmp_path / "decisions.jsonl"),
            "results_dir": str(tmp_path / "logs"),
            "data_cache_dir": str(tmp_path / "cache"),
        }
    )
    app = create_app()
    with TestClient(app) as c:
        yield c
    reset_config()


@pytest.mark.unit
def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


@pytest.mark.unit
def test_list_runs_empty(client):
    r = client.get("/api/runs")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.unit
def test_get_run_404(client):
    r = client.get("/api/runs/nonexistent")
    assert r.status_code == 404


@pytest.mark.unit
def test_start_run_validates_ticker(client):
    r = client.post("/api/runs", json={"ticker": "", "trade_date": "2026-09-01"})
    assert r.status_code == 422


@pytest.mark.unit
def test_start_run_validates_date_format(client):
    r = client.post("/api/runs", json={"ticker": "NVDA", "trade_date": "not-a-date"})
    assert r.status_code == 422


@pytest.mark.unit
def test_start_run_rejects_bad_portfolio(client):
    r = client.post(
        "/api/runs",
        json={
            "ticker": "NVDA",
            "trade_date": "2026-09-01",
            "portfolio": {"positions": [{"quantity": "x"}]},
        },
    )
    assert r.status_code == 400


@pytest.mark.unit
def test_decisions_endpoints_empty(client):
    r = client.get("/api/decisions")
    assert r.status_code == 200
    assert r.json() == []
    r = client.get("/api/decisions/tickers")
    assert r.json() == []


@pytest.mark.unit
def test_backtest_validates_dates(client):
    r = client.post(
        "/api/backtests",
        json={
            "tickers": ["NVDA"],
            "start": "not-a-date",
            "end": "2026-09-01",
        },
    )
    assert r.status_code == 422


@pytest.mark.unit
def test_backtest_rejects_empty_grid(client):
    r = client.post(
        "/api/backtests",
        json={
            "tickers": ["NVDA"],
            "start": "2999-01-01",
            "end": "2999-01-05",
        },
    )
    assert r.status_code == 400
    assert "no dates" in r.json()["detail"]
