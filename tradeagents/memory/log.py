"""Append-only JSONL decision log.

One JSON object per line. This shape was chosen over the markdown-with-comment-
delimiters design because every operation the log actually performs — append a
decision, find pending entries for a ticker, update one entry after settlement,
filter by date — is a filter over structured records. Parsing that structure
back out of prose is where most of a markdown log's bugs live.

Concurrency: appends and updates each rewrite the file atomically (write to a
temp file, then ``os.replace``). Two processes writing at once may lose one
append — the log never corrupts, but last-write-wins. A CLI that runs one graph
per process is fine; a scheduler that launches many in parallel is not.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class DecisionLog:
    """JSONL decision log. One instance per log file."""

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    # ---- read -----------------------------------------------------------

    def all_entries(self) -> list[dict]:
        """Every entry in file order. Malformed lines are skipped with a warning.

        Skipping is deliberate: a truncated final line (a crash mid-write before
        the atomic rename) would otherwise make the whole log unreadable and
        lose every prior decision with it.
        """
        if not self.path.exists():
            return []
        entries: list[dict] = []
        for i, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as exc:
                logger.warning("Skipping malformed decision-log line %d: %s", i, exc)
        return entries

    def has(self, ticker: str, trade_date: str) -> bool:
        """Whether an entry for this ticker and date already exists.

        Guards a re-run of the same analysis: recording the decision twice would
        count it twice in every aggregate.
        """
        return any(
            e["ticker"] == ticker and e["trade_date"] == trade_date
            for e in self.all_entries()
        )

    def pending_for(self, ticker: str) -> list[dict]:
        """Unsettled entries for one ticker, oldest first.

        Oldest first so a settlement pass resolves them in the order they were
        made — a reflection generated later benefits from the ones generated
        earlier in the same pass, if a future version chooses to chain them.
        """
        return sorted(
            (
                e
                for e in self.all_entries()
                if e["ticker"] == ticker and not e.get("settled")
            ),
            key=lambda e: e["trade_date"],
        )

    # ---- write ----------------------------------------------------------

    def record(self, entry: dict) -> bool:
        """Append one decision. Returns False (and does nothing) if it already exists.

        The caller writes the fields; this class only owns the file. Required
        keys: ``ticker``, ``trade_date``, ``rating``, ``decision``. Anything else
        is stored verbatim and read back by callers that know about it.
        """
        for key in ("ticker", "trade_date", "rating", "decision"):
            if key not in entry:
                raise ValueError(f"decision entry is missing required key {key!r}")
        if self.has(entry["ticker"], entry["trade_date"]):
            logger.info(
                "Skipping duplicate decision entry for %s on %s",
                entry["ticker"],
                entry["trade_date"],
            )
            return False

        record = {**entry, "created_at": _now()}
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return True

    def settle(
        self,
        ticker: str,
        trade_date: str,
        *,
        raw_return: float,
        alpha_return: float,
        holding_days: int,
        resolved_date: str,
        benchmark: str,
        reflection: str,
    ) -> bool:
        """Mark one entry settled, in a single atomic rewrite.

        Returns False when no pending entry matches — the entry was already
        settled by a concurrent run, or the ticker and date are wrong.
        """
        entries = self.all_entries()
        found = False
        for e in entries:
            if (
                e["ticker"] == ticker
                and e["trade_date"] == trade_date
                and not e.get("settled")
            ):
                e.update(
                    {
                        "settled": True,
                        "raw_return": raw_return,
                        "alpha_return": alpha_return,
                        "holding_days": holding_days,
                        "resolved_date": resolved_date,
                        "benchmark": benchmark,
                        "reflection": reflection,
                        "settled_at": _now(),
                    }
                )
                found = True
                break
        if not found:
            return False
        self._rewrite(entries)
        return True

    def _rewrite(self, entries: list[dict]) -> None:
        """Atomic full-file rewrite. Used only after a settle modifies one entry."""
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        os.replace(tmp, self.path)

    # ---- human-readable view -------------------------------------------

    def render_markdown(self) -> str:
        """A prose view of every entry, for reading the file by eye.

        Not the storage format — the storage is JSONL. This is what a user gets
        from ``tradingagents --show-memory`` or from a quick script, so the log
        stays pleasant to skim without giving up the structured backing.
        """
        lines = ["# Decision log", ""]
        for e in self.all_entries():
            tag = (
                f"[{e['trade_date']} | {e['ticker']} | {e['rating']}"
                + (
                    f" | {e['raw_return']:+.1%} raw | {e['alpha_return']:+.1%} alpha"
                    f" | {e['holding_days']}d vs {e['benchmark']} | resolved {e['resolved_date']}"
                    if e.get("settled")
                    else " | pending"
                )
                + "]"
            )
            lines += [tag, "", "## Decision", "", e.get("decision", ""), ""]
            if e.get("reflection"):
                lines += ["## Reflection", "", e["reflection"], ""]
            lines += ["---", ""]
        return "\n".join(lines)


def _now() -> str:
    """ISO-8601 to the second, local time.

    Local rather than UTC because a human reading the log is the primary
    consumer; the trade_date field carries the point-in-time semantics.
    """
    return datetime.now().isoformat(timespec="seconds")
