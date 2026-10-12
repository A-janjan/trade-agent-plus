"""Write a completed run's reports to disk.

Two artifacts, both useful for different consumers:

  * ``complete_report.md`` — the whole run in one file, sections in pipeline
    order, ready to read top to bottom.
  * ``run.json`` — a machine-readable summary: ticker, date, rating, models,
    config snapshot, and any settled prior decisions. A run directory should
    say what produced it without the reader consulting external state.

Per-section markdown files are written alongside, so a script that wants only
the trader's proposal does not have to slice the whole report. Which sections
exist, what they are called, and how each is extracted is one registry — adding
a section is a registry entry, not a code change.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tradeagents.dataflows.symbols import safe_ticker_component

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Section:
    """One section of a run report."""

    key: str  # directory slug, e.g. "analysts"
    title: str  # heading text
    filename: str  # file within the directory, e.g. "market.md"
    extractor: Callable[[dict], str | None]  # state -> content, or None to skip


# The report structure. Order matters: sections appear in this order in the
# combined report, and directories are numbered by their position so a file
# browser sorts them as the pipeline runs.
SECTIONS: tuple[Section, ...] = (
    Section("analysts", "Analyst Team", "market.md", lambda s: s.get("market_report")),
    Section(
        "analysts", "Analyst Team", "sentiment.md", lambda s: s.get("sentiment_report")
    ),
    Section("analysts", "Analyst Team", "news.md", lambda s: s.get("news_report")),
    Section(
        "analysts",
        "Analyst Team",
        "fundamentals.md",
        lambda s: s.get("fundamentals_report"),
    ),
    Section(
        "research",
        "Research Debate",
        "upside.md",
        lambda s: _turn(s, "research_debate", "upside"),
    ),
    Section(
        "research",
        "Research Debate",
        "downside.md",
        lambda s: _turn(s, "research_debate", "downside"),
    ),
    Section(
        "research", "Research Debate", "lead.md", lambda s: s.get("investment_plan")
    ),
    Section(
        "trading", "Trading", "trader.md", lambda s: s.get("trader_investment_plan")
    ),
    Section(
        "risk", "Risk Debate", "growth.md", lambda s: _turn(s, "risk_debate", "growth")
    ),
    Section(
        "risk",
        "Risk Debate",
        "capital.md",
        lambda s: _turn(s, "risk_debate", "capital"),
    ),
    Section(
        "risk",
        "Risk Debate",
        "balanced.md",
        lambda s: _turn(s, "risk_debate", "balanced"),
    ),
    Section(
        "portfolio",
        "Portfolio Manager",
        "decision.md",
        lambda s: s.get("final_trade_decision"),
    ),
)


def _turn(state: dict, debate_key: str, speaker: str) -> str | None:
    """Concatenate every turn a speaker took in a debate.

    A participant who spoke twice is one section, not two — the reader cares
    about their argument, not about which round each paragraph came from.
    """
    debate = state.get(debate_key) or {}
    turns = [
        t["content"] for t in debate.get("transcript", []) if t["speaker"] == speaker
    ]
    return "\n\n".join(turns) if turns else None


def write_report_tree(
    final_state: dict,
    ticker: str,
    save_path: str | Path,
    *,
    config: dict | None = None,
    settled: list[dict] | None = None,
    past_context: str = "",
) -> Path:
    """Write a run's reports under ``save_path``; return the path to ``complete_report.md``.

    ``config``, ``settled``, and ``past_context`` are optional context that
    enrich ``run.json`` and the combined report. All three are exactly what
    ``TradingGraph.propagate`` already produced — the caller passes them so the
    report is self-contained rather than requiring a reader to reconstruct
    what happened from the on-disk decision log.
    """
    root = Path(save_path)
    root.mkdir(parents=True, exist_ok=True)
    ticker = safe_ticker_component(ticker)

    # --- per-section files, numbered so a file browser sorts as the pipeline ran
    section_dirs: dict[str, Path] = {}
    for i, section in enumerate(SECTIONS, start=1):
        content = section.extractor(final_state)
        if not content:
            continue
        dir_name = (
            f"{i:02d}_{section.key}"
            if section.key not in section_dirs
            else _dir_for(section, SECTIONS)
        )
        # Reuse an already-created directory for the same section key.
        existing = next(
            (
                p
                for p in root.iterdir()
                if p.is_dir() and p.name.endswith(f"_{section.key}")
            ),
            None,
        )
        section_dir = existing or (root / dir_name)
        section_dir.mkdir(exist_ok=True)
        (section_dir / section.filename).write_text(content, encoding="utf-8")
        section_dirs.setdefault(section.key, section_dir)

    # --- combined report, sections in pipeline order
    header = f"# Trading analysis report: {ticker}\n\n"
    header += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    parts = [header]
    if past_context:
        parts.append("## Prior lessons applied\n\n" + past_context + "\n\n")
    if settled:
        parts.append(
            "## Prior decisions settled this run\n\n"
            + _render_settled(settled)
            + "\n\n"
        )

    # Group by section so consecutive analysts share one heading.
    current_key: str | None = None
    for section in SECTIONS:
        content = section.extractor(final_state)
        if not content:
            continue
        if section.key != current_key:
            parts.append(f"## {section.title}\n\n")
            current_key = section.key
        parts.append(
            f"### {section.filename.removesuffix('.md').capitalize()}\n\n{content}\n\n"
        )

    (root / "complete_report.md").write_text("".join(parts), encoding="utf-8")

    # --- machine-readable run summary
    run_meta = {
        "ticker": ticker,
        "trade_date": final_state.get("trade_date"),
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "rating": final_state.get("final_rating") or None,
        "models": {
            "provider": (config or {}).get("llm_provider"),
            "quick": (config or {}).get("quick_think_llm"),
            "deep": (config or {}).get("deep_think_llm"),
        },
        "config_snapshot": _config_snapshot(config or {}),
        "settled_count": len(settled or []),
    }
    (root / "run.json").write_text(json.dumps(run_meta, indent=2), encoding="utf-8")

    return root / "complete_report.md"


def _dir_for(section: Section, sections: tuple[Section, ...]) -> str:
    """Directory name for a section: ``<n>_<key>`` where ``n`` is its first position."""
    for i, s in enumerate(sections, start=1):
        if s.key == section.key:
            return f"{i:02d}_{section.key}"
    return section.key


def _config_snapshot(config: dict) -> dict[str, Any]:
    """The subset of config that determines the report's content.

    A full config dict can carry API keys or paths; a snapshot for the report
    should not. These keys are the ones a reader would want to know when
    reproducing the run: which vendors, which debates, which language.
    """
    keys = (
        "max_debate_rounds",
        "max_risk_discuss_rounds",
        "holding_period_days",
        "output_language",
        "data_vendors",
        "benchmark_ticker",
    )
    return {k: config[k] for k in keys if k in config}


def _render_settled(settled: list[dict]) -> str:
    """A small markdown table of prior decisions settled on this run's way in."""
    lines = [
        "| Prior date | Rating | Raw | Alpha | Window | Benchmark |",
        "|---|---|---:|---:|---:|---|",
    ]
    for e in settled:
        lines.append(
            f"| {e['trade_date']} | {e['rating']} | "
            f"{e['raw_return']:+.1%} | {e['alpha_return']:+.1%} | "
            f"{e['holding_days']}d | {e['benchmark']} |"
        )
    return "\n".join(lines)
