"""In-memory registry of active and recent runs, with per-run pub/sub.

A run is an asyncio task that drives the graph and pushes every event into a
per-run broadcast channel. Subscribers (SSE connections) get the full event
history first, then live events. Completed runs keep their history for the
process lifetime; a client that wants to revisit a run after the server
restarts reads the on-disk artifacts instead (see ``routers/runs.py``).

Why in-memory: the API is a live view over a pipeline that runs once. There is
no shared mutable state to synchronize across processes, so a queue + a list is
enough. A production deployment that wants horizontal scaling would replace
this with a Redis-backed event log; that is out of scope.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from tradeagents.api import events as ev
from tradeagents.graph.progress import stream_events
from tradeagents.graph.trading_graph import TradingGraph
from tradeagents.portfolio import PortfolioContext

logger = logging.getLogger(__name__)

Status = Literal["running", "done", "failed"]


@dataclass
class RunHandle:
    """A run's state and its subscriber list."""

    run_id: str
    ticker: str
    trade_date: str
    asset_type: str
    started_at: float
    status: Status = "running"
    events: list[dict] = field(default_factory=list)
    state: dict | None = None
    error: str | None = None
    elapsed_seconds: float | None = None
    _subscribers: list[asyncio.Queue] = field(default_factory=list)
    _task: asyncio.Task | None = None
    _events_file: Path | None = None

    def subscribe(self) -> asyncio.Queue:
        """A queue that receives every event published after this call.

        A run that has already finished has already sent its ``None`` sentinel
        to every prior subscriber; a fresh subscriber would wait for one that
        will never arrive. Send it now, so a client that connects after the
        run finishes gets the replayed history and then a clean close.
        """
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(q)
        if self.status != "running":
            q.put_nowait(None)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        if q in self._subscribers:
            self._subscribers.remove(q)

    async def publish(self, event: dict) -> None:
        """Append to history, write to disk, deliver to subscribers."""
        self.events.append(event)
        if self._events_file is not None:
            try:
                with open(self._events_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
            except OSError as exc:
                logger.warning("Could not append to events file: %s", exc)
        for q in list(self._subscribers):
            q.put_nowait(event)

    def close_subscribers(self) -> None:
        """Send a sentinel so each SSE generator can exit its loop cleanly."""
        for q in list(self._subscribers):
            q.put_nowait(None)


class RunManager:
    """Registry of runs. One per API process."""

    def __init__(self, config: dict):
        self.config = config
        self._runs: dict[str, RunHandle] = {}
        self._runs_dir = Path(config["results_dir"]) / "api_runs"
        self._runs_dir.mkdir(parents=True, exist_ok=True)

    def get(self, run_id: str) -> RunHandle | None:
        return self._runs.get(run_id)

    def list(self) -> list[RunHandle]:
        return sorted(self._runs.values(), key=lambda r: r.started_at, reverse=True)

    async def start(
        self,
        ticker: str,
        trade_date: str,
        *,
        asset_type: str = "stock",
        selected_analysts: tuple[str, ...] = (
            "market",
            "social",
            "news",
            "fundamentals",
        ),
        portfolio: PortfolioContext | None = None,
    ) -> RunHandle:
        """Create a RunHandle and launch the graph in a background task."""
        run_id = uuid.uuid4().hex[:12]
        run_dir = self._runs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        handle = RunHandle(
            run_id=run_id,
            ticker=ticker,
            trade_date=trade_date,
            asset_type=asset_type,
            started_at=time.time(),
            _events_file=run_dir / "events.jsonl",
        )
        self._runs[run_id] = handle
        handle._task = asyncio.create_task(
            self._drive(handle, selected_analysts, portfolio)
        )
        return handle

    async def _drive(
        self,
        handle: RunHandle,
        selected_analysts: tuple[str, ...],
        portfolio: PortfolioContext | None,
    ) -> None:
        """Run the graph, forwarding each event into the handle."""
        config = {**self.config, "streaming": True}
        models = {
            "provider": config.get("llm_provider"),
            "quick": config.get("quick_think_llm"),
            "deep": config.get("deep_think_llm"),
        }
        await handle.publish(
            ev.run_started(handle.run_id, handle.ticker, handle.trade_date, models, selected_analysts=list(selected_analysts),)
        )

        try:
            graph = TradingGraph(selected_analysts, config=config)
            state = graph._initial_state(
                handle.ticker,
                handle.trade_date,
                handle.asset_type,
                portfolio,
            )
            # Settle on the way in, matching propagate()'s behavior, and emit
            # what was learned as its own event so the UI can surface it.
            settled = graph._settle(handle.ticker)
            if settled:
                await handle.publish(ev.settled(settled))

            cfg = dict(
                graph.build_run_config(
                    handle.ticker,
                    handle.trade_date,
                    asset_type=handle.asset_type,
                )
            )

            final: dict = dict(state)
            async for event in stream_events(graph.graph, state, cfg):
                await handle.publish(event)
                if event["type"] == "run.state":
                    # The graph's own final state — reports, debates, decision,
                    # everything. Replaces per-event accumulation, which only
                    # ever saw the events it was told to look for.
                    final = event["state"]

            final["company_of_interest"] = handle.ticker
            final["trade_date"] = handle.trade_date
            final["asset_type"] = handle.asset_type
            final["settled"] = settled
            handle.state = final
            handle.status = "done"
            handle.elapsed_seconds = round(time.time() - handle.started_at, 2)

            # Persist a final state file so a restart can replay the run.
            (self._runs_dir / handle.run_id / "state.json").write_text(
                json.dumps(final, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )

            await handle.publish(
                ev.run_finished(
                    handle.run_id,
                    final.get("final_rating") or None,
                    handle.elapsed_seconds,
                )
            )
        except Exception as exc:  # noqa: BLE001 — surface any failure as an event
            logger.exception("Run %s failed", handle.run_id)
            handle.status = "failed"
            handle.error = str(exc)
            await handle.publish(ev.run_failed(handle.run_id, str(exc)))
        finally:
            handle.close_subscribers()

    async def cancel(self, run_id: str) -> bool:
        handle = self._runs.get(run_id)
        if handle is None or handle._task is None or handle._task.done():
            return False
        handle._task.cancel()
        return True
