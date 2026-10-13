"""Decision log endpoints: list settled and pending decisions, render markdown."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/decisions", tags=["decisions"])


def _log(request: Request):
    return request.app.state.decision_log


@router.get("")
async def list_decisions(request: Request, ticker: str | None = None) -> list[dict]:
    entries = _log(request).all_entries()
    if ticker:
        entries = [e for e in entries if e["ticker"] == ticker.upper()]
    # Most recent first; the log is in write order, which is roughly date order.
    return sorted(entries, key=lambda e: e["trade_date"], reverse=True)


@router.get("/markdown")
async def get_markdown(request: Request) -> dict:
    return {"markdown": _log(request).render_markdown()}


@router.get("/tickers")
async def list_tickers(request: Request) -> list[str]:
    seen: set[str] = set()
    for e in _log(request).all_entries():
        seen.add(e["ticker"])
    return sorted(seen)


class SettleRequest(BaseModel):
    ticker: str | None = None


@router.post("/settle")
async def settle(request: Request, body: SettleRequest) -> dict:
    """Force a settlement pass. Useful in a UI to refresh outcomes on demand."""
    graph_llm = request.app.state.settle_llm
    log = _log(request)
    from tradeagents.memory.settlement import settle_pending

    tickers = (
        [body.ticker.upper()]
        if body.ticker
        else list({e["ticker"] for e in log.pending_for_all()})
    )
    settled: list[dict] = []
    for t in tickers:
        settled.extend(settle_pending(t, log, graph_llm, request.app.state.config))
    return {"settled_count": len(settled), "entries": settled}
