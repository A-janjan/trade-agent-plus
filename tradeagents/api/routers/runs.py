"""Run endpoints: start, list, get, stream, cancel.

Streaming is Server-Sent Events. A client that connects mid-run gets the
event history first, then live events. A client that connects after the run
completes gets the history and an immediate close, so a page reload never
misses events.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from tradeagents.portfolio import PortfolioContext

router = APIRouter(prefix="/api/runs", tags=["runs"])


class StartRunRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=32)
    trade_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    asset_type: str = "stock"
    selected_analysts: list[str] = Field(
        default_factory=lambda: ["market", "social", "news", "fundamentals"]
    )
    portfolio: dict | None = None


def _manager(request: Request):
    return request.app.state.run_manager


def _handle_to_dict(h) -> dict:
    return {
        "run_id": h.run_id,
        "ticker": h.ticker,
        "trade_date": h.trade_date,
        "asset_type": h.asset_type,
        "status": h.status,
        "started_at": h.started_at,
        "elapsed_seconds": h.elapsed_seconds,
        "error": h.error,
        "rating": (h.state or {}).get("final_rating") if h.state else None,
        "event_count": len(h.events),
    }


@router.post("")
async def start_run(body: StartRunRequest, request: Request) -> dict:
    portfolio = None
    if body.portfolio is not None:
        try:
            portfolio = PortfolioContext.model_validate(body.portfolio)
        except Exception as exc:  # noqa: BLE001 — surface validation as a 400
            raise HTTPException(
                status_code=400, detail=f"portfolio is not usable: {exc}"
            ) from exc

    handle = await _manager(request).start(
        body.ticker,
        body.trade_date,
        asset_type=body.asset_type,
        selected_analysts=tuple(body.selected_analysts),
        portfolio=portfolio,
    )
    return _handle_to_dict(handle)


@router.get("")
async def list_runs(request: Request) -> list[dict]:
    return [_handle_to_dict(h) for h in _manager(request).list()]


@router.get("/{run_id}")
async def get_run(run_id: str, request: Request) -> dict:
    handle = _manager(request).get(run_id)
    if handle is None:
        raise HTTPException(status_code=404, detail="run not found")
    return {**_handle_to_dict(handle), "state": handle.state}


@router.delete("/{run_id}")
async def cancel_run(run_id: str, request: Request) -> dict:
    ok = await _manager(request).cancel(run_id)
    if not ok:
        raise HTTPException(status_code=404, detail="run not found or already finished")
    return {"cancelled": True}


@router.get("/{run_id}/stream")
async def stream_run(run_id: str, request: Request) -> EventSourceResponse:
    handle = _manager(request).get(run_id)
    if handle is None:
        raise HTTPException(status_code=404, detail="run not found")

    async def event_source():
        # Subscribe first. Between this call and the snapshot below, no other
        # coroutine runs (both are synchronous), so no event can be published
        # in the gap and missed. If the run has already finished, subscribe
        # seeds the queue with the None sentinel so the loop below terminates
        # without relying on the status check.
        queue = handle.subscribe()
        try:
            snapshot = list(handle.events)
            for event in snapshot:
                yield {"data": json.dumps(event, default=str)}

            while True:
                if await request.is_disconnected():
                    return
                event = await queue.get()
                if event is None:
                    return
                yield {"data": json.dumps(event, default=str)}
        finally:
            handle.unsubscribe(queue)

    return EventSourceResponse(event_source())


@router.get("/{run_id}/events")
async def get_events(run_id: str, request: Request) -> list[dict]:
    """Full event log. Useful for replay without opening an SSE stream."""
    handle = _manager(request).get(run_id)
    if handle is None:
        raise HTTPException(status_code=404, detail="run not found")
    return handle.events
