"""Live terminal display for a running graph.

The pipeline is six-plus nodes deep and each can take several seconds, so the
final-answer-only output reads as a hang. This module consumes LangGraph's
stream and renders what is actually happening: which node is running, how long
each has taken, and a rolling preview of the text the active node is producing.

Driven by two stream modes together:

  * ``updates`` — one event per completed node; drives the row checkmarks.
  * ``messages`` — LLM tokens with the emitting node in ``metadata``; drives
    the live preview and per-node output size.

A third mode, ``values``, carries the complete state after each step; its last
payload is the run's final state, which is why the driver uses it rather than
merging ``updates`` by hand (message lists append, so a naive merge would lose
them).

Token granularity depends on the model actually streaming. A model call that
returns in one block still populates the row, just without an intermediate
preview.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


@dataclass
class _NodeRow:
    """One node's contribution to the display."""

    name: str
    started: float
    finished: float | None = None
    chars: int = 0
    tool_calls: int = 0

    @property
    def elapsed(self) -> float:
        return (self.finished or time.monotonic()) - self.started

    @property
    def done(self) -> bool:
        return self.finished is not None


class ProgressDisplay:
    """A Rich live region tracking node-by-node pipeline progress.

    Not thread-safe; one display per run, driven from the streaming loop.
    ``stop()`` renders a final frame with every row settled, so a completed run
    leaves its summary table on screen rather than clearing to nothing.
    """

    def __init__(
        self,
        *,
        title: str,
        console: Console | None = None,
        preview_lines: int = 5,
        refresh_per_second: float = 8.0,
        show_preview: bool = True,
    ):
        self.console = console or Console()
        self.title = title
        self.preview_lines = preview_lines
        self.refresh_per_second = refresh_per_second
        self.show_preview = show_preview

        self._rows: list[_NodeRow] = []
        self._by_name: dict[str, _NodeRow] = {}
        self._preview: dict[str, str] = {}
        self._active: str = ""
        self._live: Live | None = None
        self._finished = False

    # ---- lifecycle ------------------------------------------------------

    def start(self) -> None:
        if self._live is not None:
            return
        self._live = Live(
            self._render(),
            console=self.console,
            refresh_per_second=self.refresh_per_second,
            transient=False,
        )
        self._live.start()

    def stop(self) -> None:
        if self._live is None:
            return
        self._finished = True
        self._live.update(self._render())
        self._live.stop()
        self._live = None

    # ---- events ---------------------------------------------------------

    def token(self, node: str, text: str) -> None:
        """A streamed fragment of the node's output."""
        if not node or not text:
            return
        row = self._row(node)
        row.chars += len(text)
        # Keep only the tail: the preview is a rolling window, and a node that
        # emits 20k characters should not grow this buffer without bound.
        self._preview[node] = (self._preview.get(node, "") + text)[-1200:]
        self._active = node
        self._refresh()

    def node_finished(self, node: str) -> None:
        """Mark a node complete; ``updates`` fires once per node, so guard
        against a second call for the same node."""
        row = self._by_name.get(node)
        if row is not None and row.finished is None:
            row.finished = time.monotonic()
        self._active = ""
        self._refresh()

    def note(self, node: str, message: str) -> None:
        """Attach a short status line to a node (e.g. a tool call it made)."""
        row = self._row(node)
        row.tool_calls += 1
        self._preview[node] = f"{message}\n{self._preview.get(node, '')}"[:1200]
        self._refresh()

    # ---- rendering ------------------------------------------------------

    def _row(self, name: str) -> _NodeRow:
        row = self._by_name.get(name)
        if row is None:
            row = _NodeRow(name=name, started=time.monotonic())
            self._by_name[name] = row
            self._rows.append(row)
        return row

    def _refresh(self) -> None:
        if self._live is not None:
            self._live.update(self._render())

    def _status_cell(self, row: _NodeRow) -> Text:
        if row.finished is not None:
            return Text("✓", style="green")
        if row.name == self._active or self._rows[-1] is row:
            return Text("⠹", style="yellow")
        return Text("·", style="dim")

    def _render(self) -> RenderableType:
        """Render the current state of the display as a Rich renderable."""
        header = Text(self.title, style="bold cyan")

        table = Table.grid(padding=(0, 2))
        table.add_column(width=1)  # status
        table.add_column(ratio=1)  # node name
        table.add_column(justify="right")  # elapsed
        table.add_column(justify="right")  # extra

        for row in self._rows:
            extra = (
                f"{row.tool_calls} tools"
                if row.tool_calls
                else (f"{row.chars:,} chars" if row.chars else "")
            )
            table.add_row(
                self._status_cell(row),
                Text(row.name, style="white" if not row.done else "dim white"),
                Text(f"{row.elapsed:5.1f}s", style="dim"),
                Text(extra, style="dim"),
            )

        if not self._rows:
            table.add_row(
                Text("⠹", style="yellow"), Text("starting…", style="dim"), "", ""
            )

        parts: list[RenderableType] = [header, table]
        preview = self._active_preview()
        if preview:
            parts.append(
                Panel(
                    preview,
                    title=f"[dim]{self._active}[/dim]",
                    title_align="left",
                    border_style="dim",
                    padding=(0, 1),
                )
            )
        return Group(*parts)

    def _active_preview(self) -> Text:
        """Return a dim italic preview of the active node's output, or an empty string if none."""
        if not self.show_preview or not self._active:
            return Text("")
        raw = self._preview.get(self._active, "").strip()
        if not raw:
            return Text("")
        lines = raw.splitlines()[-self.preview_lines :]
        return Text("\n".join(lines), style="dim italic", overflow="ellipsis")


# ---------------------------------------------------------------------------
# Stream driver
# ---------------------------------------------------------------------------


def _unpack(item) -> tuple[str, object]:
    """Normalize a multi-mode stream item to ``(mode, payload)``.

    LangGraph yields ``(mode, payload)`` tuples when given a list of stream
    modes. Older releases yielded a single-key dict instead; accepting both
    costs three lines and removes a version pin.
    """
    if isinstance(item, tuple) and len(item) == 2:
        return item  # type: ignore[return-value]
    if isinstance(item, dict) and len(item) == 1:
        return next(iter(item.items()))
    raise ValueError(f"Unrecognized stream item: {item!r}")


def _chunk_text(chunk) -> str:
    """Extract text from an LLM chunk whose content may be a string or blocks."""
    content = getattr(chunk, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return ""


def stream_graph(
    graph,
    inputs,
    config: dict,
    display: ProgressDisplay,
) -> dict:
    """Run ``graph`` with live progress, and return its final state.

    The ``values`` stream mode carries the complete state after each step, so
    the last payload is authoritative — no need to fold ``updates`` into a
    state dict, which would drop appended message lists.

    An error mid-stream still stops the display: the caller sees the completed
    nodes plus a traceback, not a frozen spinner.
    """
    final: dict = {}
    display.start()
    try:
        stream = graph.stream(
            inputs,
            config=config,
            stream_mode=["values", "updates", "messages"],
        )
        for item in stream:
            mode, payload = _unpack(item)

            if mode == "values" and isinstance(payload, dict):
                final = payload

            elif mode == "messages":
                chunk, metadata = payload  # type: ignore[misc]
                node = (metadata or {}).get("langgraph_node", "")
                text = _chunk_text(chunk)
                if text:
                    display.token(node, text)

            elif mode == "updates" and isinstance(payload, dict):
                for node, update in payload.items():
                    # A tool node's update carries the ToolMessages it produced;
                    # surface the tool names so a slow tool shows as work, not a stall.
                    if isinstance(update, dict):
                        for msg in update.get("messages", []) or []:
                            name = getattr(msg, "name", None)
                            if name:
                                display.note(node, f"→ {name}")
                    display.node_finished(node)
    finally:
        display.stop()
    return final


async def stream_events(graph, inputs, config: dict):
    """Async generator of the API's normalized events for one graph run.

    Streams three modes together:

      * ``messages`` — LLM tokens, tagged with the emitting node, for the
        live preview.
      * ``updates`` — one delta per completed node. A node's update contains
        exactly what that node returned, so the *content* of each report,
        each debate turn, and the final decision arrives here without
        re-scanning the whole state.
      * ``values`` — the full state after each step. Only the last payload is
        used, emitted as a single ``run.state`` event at the end of the run.

    The mapping tables in ``api.events`` (``REPORT_NODES``,
    ``DEBATE_SPEAKERS``) drive which event each node's update produces, so
    adding a report or a debate participant is a table entry.
    """
    from tradeagents.api import events as ev

    last_values: dict = {}

    async for item in graph.astream(
        inputs,
        config=config,
        stream_mode=["values", "updates", "messages"],
    ):
        mode, payload = _unpack(item)

        if mode == "values":
            if isinstance(payload, dict):
                last_values = payload

        elif mode == "messages":
            if not isinstance(payload, tuple) or len(payload) != 2:
                continue
            chunk, metadata = payload
            metadata = metadata if isinstance(metadata, dict) else {}
            node = metadata.get("langgraph_node", "")
            text = _chunk_text(chunk)
            if text and node:
                yield ev.token(node, text)

        elif mode == "updates":
            if not isinstance(payload, dict):
                continue
            for node, update in payload.items():
                if isinstance(update, dict):
                    for event in _events_for_node(ev, node, update):
                        yield event
                yield ev.node_finished(node)

    # The final full state. Emitted once, after every node has finished, so
    # a late subscriber or a reconnecting client can rebuild the whole view.
    if last_values:
        yield ev.run_state(last_values)


def _events_for_node(ev, node: str, update: dict):
    """The per-content events a single node's update produces.

    Three kinds of node produce content that the UI shows as its own thing:
    a report-writing analyst or synthesizer, a debate participant, and the
    portfolio manager. Each is looked up by node name in the tables from
    ``api.events`` — this function never names an agent directly.
    """
    # Tool calls made by this node (only nodes with tools produce these).
    for msg in update.get("messages", []) or []:
        name = getattr(msg, "name", None)
        if name:
            yield ev.tool_finished(node, name)

    # A report, when the node's update carries one with content. The check
    # for a non-empty string is what filters out the interim updates during a
    # tool-calling loop: the market analyst returns ``{"market_report": ""}``
    # on every pass while it is still gathering data, and only the final pass
    # returns actual text.
    report_key = ev.REPORT_NODES.get(node)
    if report_key:
        value = update.get(report_key)
        if isinstance(value, str) and value.strip():
            yield ev.report(report_key, value)

    # One debate turn, when the node is a debate participant. The update
    # carries the whole transcript at that node's state key; the last turn
    # is the one this node just added.
    debate_info = ev.DEBATE_SPEAKERS.get(node)
    if debate_info:
        debate_key, _ = debate_info
        transcript = (update.get(debate_key) or {}).get("transcript") or []
        if transcript:
            last = transcript[-1]
            yield ev.debate_turn(debate_key, last["speaker"], last["content"])

    # The final decision, when the node is the portfolio manager. Its update
    # carries both the rendered markdown and the structured rating.
    if node == "Portfolio Manager":
        text = update.get("final_trade_decision") or ""
        if text:
            yield ev.decision(
                {
                    "final_rating": update.get("final_rating") or "",
                    "final_trade_decision": text,
                }
            )
