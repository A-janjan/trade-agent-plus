from __future__ import annotations

import json

import pytest

from tradeagents.reporting import SECTIONS, write_report_tree


def _state(**overrides):
    state = {
        "trade_date": "2026-09-01",
        "market_report": "Trend up.",
        "sentiment_report": "Mixed.",
        "news_report": "Macro quiet.",
        "fundamentals_report": "Margins strong.",
        "investment_plan": "**Stance**: Buy",
        "trader_investment_plan": "**Action**: Buy",
        "final_trade_decision": "**Rating**: Buy",
        "final_rating": "Buy",
        "research_debate": {
            "transcript": [
                {"speaker": "upside", "content": "Bull case A."},
                {"speaker": "downside", "content": "Bear case A."},
                {"speaker": "upside", "content": "Bull case B."},
            ],
            "max_rounds": 1,
            "verdict": "",
        },
        "risk_debate": {
            "transcript": [
                {"speaker": "growth", "content": "Go big."},
                {"speaker": "capital", "content": "Go small."},
                {"speaker": "balanced", "content": "Middle."},
            ],
            "max_rounds": 1,
            "verdict": "",
        },
    }
    state.update(overrides)
    return state


@pytest.mark.unit
def test_writes_complete_report(tmp_path):
    path = write_report_tree(_state(), "NVDA", tmp_path)
    assert path.exists()
    assert path.name == "complete_report.md"
    text = path.read_text()
    assert "Trading analysis report: NVDA" in text
    assert "Trend up." in text
    assert "**Rating**: Buy" in text


@pytest.mark.unit
def test_writes_run_json(tmp_path):
    write_report_tree(
        _state(),
        "NVDA",
        tmp_path,
        config={
            "llm_provider": "openai",
            "quick_think_llm": "gpt-4o-mini",
            "deep_think_llm": "gpt-4o",
            "max_debate_rounds": 1,
            "output_language": "English",
        },
    )
    meta = json.loads((tmp_path / "run.json").read_text())
    assert meta["ticker"] == "NVDA"
    assert meta["trade_date"] == "2026-09-01"
    assert meta["rating"] == "Buy"
    assert meta["models"]["provider"] == "openai"
    assert meta["config_snapshot"]["output_language"] == "English"


@pytest.mark.unit
def test_run_json_omits_missing_sections_gracefully(tmp_path):
    state = _state()
    state["final_rating"] = ""
    write_report_tree(state, "NVDA", tmp_path)
    meta = json.loads((tmp_path / "run.json").read_text())
    assert meta["rating"] is None


@pytest.mark.unit
def test_skips_sections_with_no_content(tmp_path):
    # A run with only market selected: sentiment and news are empty and must
    # not produce empty files or orphan directories.
    state = _state(sentiment_report="", news_report="", fundamentals_report="")
    write_report_tree(state, "NVDA", tmp_path)
    analyst_dirs = [
        p for p in tmp_path.iterdir() if p.is_dir() and p.name.endswith("_analysts")
    ]
    assert len(analyst_dirs) == 1
    files = {f.name for f in analyst_dirs[0].iterdir()}
    assert files == {"market.md"}


@pytest.mark.unit
def test_debate_turns_are_concatenated(tmp_path):
    # A participant who spoke twice is one file, not two.
    write_report_tree(_state(), "NVDA", tmp_path)
    upsides = list(tmp_path.glob("*_research/upside.md"))
    assert len(upsides) == 1
    text = upsides[0].read_text()
    assert "Bull case A." in text
    assert "Bull case B." in text


@pytest.mark.unit
def test_numbered_directory_ordering(tmp_path):
    write_report_tree(_state(), "NVDA", tmp_path)
    dirs = sorted(p.name for p in tmp_path.iterdir() if p.is_dir())
    assert dirs[0].startswith("01_")
    # Directories sort in pipeline order.
    assert dirs == sorted(dirs)


@pytest.mark.unit
def test_settled_entries_render_in_report_and_run_json(tmp_path):
    settled = [
        {
            "trade_date": "2026-08-01",
            "rating": "Buy",
            "raw_return": 0.02,
            "alpha_return": 0.01,
            "holding_days": 5,
            "benchmark": "SPY",
        },
    ]
    write_report_tree(_state(), "NVDA", tmp_path, settled=settled)
    text = (tmp_path / "complete_report.md").read_text()
    assert "Prior decisions settled this run" in text
    assert "+2.0%" in text
    meta = json.loads((tmp_path / "run.json").read_text())
    assert meta["settled_count"] == 1


@pytest.mark.unit
def test_past_context_renders_at_top(tmp_path):
    write_report_tree(
        _state(),
        "NVDA",
        tmp_path,
        past_context="Past lesson from 2026-08-01.",
    )
    text = (tmp_path / "complete_report.md").read_text()
    assert "Prior lessons applied" in text
    assert "Past lesson from 2026-08-01." in text
    # Lessons precede the analyst reports.
    assert text.index("Prior lessons") < text.index("Trend up.")


@pytest.mark.unit
def test_rejects_unsafe_ticker(tmp_path):
    with pytest.raises(ValueError):
        write_report_tree(_state(), "../etc/passwd", tmp_path)


@pytest.mark.unit
def test_registry_has_all_expected_sections():
    # A structural check: if a section is dropped from the registry, this test
    # is the reminder that a report consumer may rely on it.
    filenames = {(s.key, s.filename) for s in SECTIONS}
    required = {
        ("analysts", "market.md"),
        ("analysts", "sentiment.md"),
        ("analysts", "news.md"),
        ("analysts", "fundamentals.md"),
        ("research", "upside.md"),
        ("research", "downside.md"),
        ("research", "lead.md"),
        ("trading", "trader.md"),
        ("risk", "growth.md"),
        ("risk", "capital.md"),
        ("risk", "balanced.md"),
        ("portfolio", "decision.md"),
    }
    assert required.issubset(filenames)
