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

from tradeagents.api.run_manager import RunManager
from tradeagents.api.routers import backtests, decisions, runs
from tradeagents.dataflows.config import get_config
from tradeagents.default_config import DEFAULT_CONFIG
from tradeagents.llm_clients import create_llm
from tradeagents.memory.log import DecisionLog

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    config = get_config() or DEFAULT_CONFIG.copy()
    app.state.config = config
    app.state.run_manager = RunManager(config)
    app.state.decision_log = DecisionLog(config["memory_log_path"])
    # A single LLM for settlement reflections; keeps the settle endpoint from
    # constructing a new client per request.
    app.state.settle_llm = create_llm(config, "quick")
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
