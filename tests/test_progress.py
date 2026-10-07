from __future__ import annotations

import io

import pytest
from rich.console import Console

from tradeagents.graph.progress import ProgressDisplay, _chunk_text, _unpack


@pytest.fixture
def display():
    # A Console writing to a buffer keeps the tests off the real terminal.
    return ProgressDisplay(title="test", console=Console(file=io.StringIO(), width=80))


@pytest.mark.unit
def test_display_tracks_nodes_in_order(display):
    display.token("Market Analyst", "hello ")
    display.token("Market Analyst", "world")
    display.node_finished("Market Analyst")
    display.token("News Analyst", "news")

    names = [r.name for r in display._rows]
    assert names == ["Market Analyst", "News Analyst"]
    assert display._by_name["Market Analyst"].done
    assert not display._by_name["News Analyst"].done


@pytest.mark.unit
def test_display_counts_characters(display):
    display.token("A", "12345")
    display.token("A", "678")
    assert display._by_name["A"].chars == 8


@pytest.mark.unit
def test_display_preview_is_bounded(display):
    for _ in range(500):
        display.token("A", "x" * 100)
    # The buffer keeps only the tail; unbounded growth would leak per node.
    assert len(display._preview["A"]) <= 1200


@pytest.mark.unit
def test_display_tracks_active_node(display):
    display.token("A", "text")
    assert display._active == "A"
    display.node_finished("A")
    assert display._active == ""


@pytest.mark.unit
def test_display_note_increments_tool_count(display):
    display.note("tools_market", "→ get_stock_data")
    display.note("tools_market", "→ get_indicators")
    assert display._by_name["tools_market"].tool_calls == 2


@pytest.mark.unit
def test_display_ignores_empty_tokens(display):
    display.token("A", "")
    display.token("", "text")
    assert display._rows == []


@pytest.mark.unit
def test_render_does_not_raise_when_empty(display):
    # Renders the "starting…" placeholder; the display starts before any node
    # has emitted, and that first frame must not blow up.
    display._render()


@pytest.mark.unit
def test_unpack_handles_tuple_and_dict():
    assert _unpack(("messages", {"a": 1})) == ("messages", {"a": 1})
    assert _unpack({"values": {"b": 2}}) == ("values", {"b": 2})


@pytest.mark.unit
def test_unpack_rejects_unknown_shape():
    with pytest.raises(ValueError, match="Unrecognized"):
        _unpack("nonsense")


@pytest.mark.unit
def test_chunk_text_handles_string_content():
    class Chunk:
        content = "hello"

    assert _chunk_text(Chunk()) == "hello"


@pytest.mark.unit
def test_chunk_text_handles_block_content():
    class Chunk:
        content = [
            {"type": "reasoning", "text": "ignored"},
            {"type": "text", "text": "kept "},
            {"type": "text", "text": "also"},
        ]

    assert _chunk_text(Chunk()) == "kept also"


@pytest.mark.unit
def test_chunk_text_handles_missing_content():
    class Chunk:
        pass

    assert _chunk_text(Chunk()) == ""
