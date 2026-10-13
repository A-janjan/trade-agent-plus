"""Backtest endpoints.

A backtest is a long-running batch; the endpoint returns a run_id immediately
and the client polls status. Streaming a backtest over SSE is possible (each
cell could emit events) but is deferred until the frontend needs it — for now
the summary is the interesting artifact and it is read once complete.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from tradeagents.backtest import run_backtest, summarize

router = APIRouter(prefix="/api/backtests", tags=["backtests"])


class StartBacktestRequest(BaseModel):
    tickers: list[str] = Field(min_length=1)
    start: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    end: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    every_n_days: int = Field(default=7, ge=1)
    asset_type: str = "stock"
    selected_analysts: list[str] = Field(
        default_factory=lambda: ["market", "social", "news", "fundamentals"]
    )


def _store(request: Request) -> dict:
    return request.app.state.backtests


@router.post("")
async def start_backtest(body: StartBacktestRequest, request: Request) -> dict:
    from tradeagents.backtest import iter_grid

    dates = iter_grid(body.start, body.end, body.every_n_days)
    if not dates:
        raise HTTPException(status_code=400, detail="no dates to sweep in that range")

    bt_id = uuid.uuid4().hex[:12]
    store = _store(request)
    store[bt_id] = {
        "id": bt_id,
        "status": "running",
        "tickers": body.tickers,
        "dates": dates,
        "result": None,
        "summary": None,
        "error": None,
    }

    async def worker():
        try:
            config = {**request.app.state.config}
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                lambda: run_backtest(
                    body.tickers,
                    dates,
                    config,
                    asset_type=body.asset_type,
                    selected_analysts=tuple(body.selected_analysts),
                    run_id=bt_id,
                ),
            )
            summary = summarize(result)
            store[bt_id].update(
                {
                    "status": "done",
                    "result": {
                        "run_id": result.run_id,
                        "run_dir": str(result.run_dir),
                        "cells_run": result.cells_run,
                        "cells_skipped": result.cells_skipped,
                        "cell_failures": result.cell_failures,
                        "settlement_failures": result.settlement_failures,
                    },
                    "summary": {
                        "resolved": summary.resolved,
                        "pending": summary.pending,
                        "unscored": summary.unscored,
                        "holding": summary.holding,
                        "by_rating": {
                            k: asdict(v) for k, v in summary.by_rating.items()
                        },
                    },
                }
            )
        except Exception as exc:  # noqa: BLE001
            store[bt_id].update({"status": "failed", "error": str(exc)})

    asyncio.create_task(worker())
    return {"id": bt_id, "status": "running", "tickers": body.tickers, "dates": dates}


@router.get("/{bt_id}")
async def get_backtest(bt_id: str, request: Request) -> dict:
    record = _store(request).get(bt_id)
    if record is None:
        raise HTTPException(status_code=404, detail="backtest not found")
    return record


@router.get("")
async def list_backtests(request: Request) -> list[dict]:
    return sorted(
        _store(request).values(),
        key=lambda r: r["id"],
        reverse=True,
    )
