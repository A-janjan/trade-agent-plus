"""FastAPI application.

Wires the run manager, the decision log, and the routers. Intended to run
alongside the CLI: the CLI writes decisions to the shared log, the API reads
and writes the same file. Both see the same history.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tradeagents.api.routers import backtests, decisions, runs
from tradeagents.api.run_manager import RunManager
from tradeagents.dataflows.config import get_config
from tradeagents.default_config import DEFAULT_CONFIG
from tradeagents.memory.log import DecisionLog

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    config = get_config() or DEFAULT_CONFIG.copy()
    app.state.config = config
    app.state.run_manager = RunManager(config)
    # Backtests are intentionally process-local, just like live run handles.
    # Initialize the registry here so the backtest router works in a fresh API
    # process instead of failing on the first request.
    app.state.backtests = {}
    app.state.decision_log = DecisionLog(config["memory_log_path"])
    # Construct the settlement LLM lazily. Health, history, and validation
    # endpoints should remain usable in a fresh process before a provider key
    # has been configured; the settle endpoint initializes it on demand.
    app.state.settle_llm = None
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="tradeagents API",
        version="0.1.0",
        description="HTTP API for the tradeagents pipeline.",
        lifespan=_lifespan,
    )
    # The Vite dev server proxies to us, so no CORS is needed for development;
    # this opens it up for a separately-served frontend.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(runs.router)
    app.include_router(decisions.router)
    app.include_router(backtests.router)

    @app.get("/api/health")
    async def health() -> dict:
        return {"ok": True}

    return app


app = create_app()
