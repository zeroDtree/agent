from __future__ import annotations

import io

from langchain_core.messages import AIMessage, AIMessageChunk

from zdt_agent.chat_cli.renderer import CLIStreamRenderer


def test_chunk_does_not_emit_tool_calls():
    out = io.StringIO()
    renderer = CLIStreamRenderer(show_reasoning=False, out=out)
    turn: list = []

    chunk = AIMessageChunk(
        content="",
        tool_call_chunks=[
            {"name": "multiply", "args": "", "id": "call-1", "index": 0, "type": "tool_call_chunk"},
        ],
    )
    renderer.consume_stream_part({"type": "messages", "data": (chunk, {})}, turn)

    assert "→ tool" not in out.getvalue()


def test_values_emits_complete_tool_calls():
    out = io.StringIO()
    renderer = CLIStreamRenderer(show_reasoning=False, out=out)
    turn: list = []

    ai_msg = AIMessage(
        content="",
        tool_calls=[
            {"name": "multiply", "args": {"a": 333, "b": 444}, "id": "call-1", "type": "tool_call"},
        ],
    )
    renderer.consume_stream_part(
        {"type": "values", "data": {"messages": [ai_msg]}},
        turn,
    )

    output = out.getvalue()
    assert '→ tool multiply {"a": 333, "b": 444}' in output
    assert len(turn) == 1


def test_values_dedupes_same_tool_call_id():
    out = io.StringIO()
    renderer = CLIStreamRenderer(show_reasoning=False, out=out)
    turn: list = []

    ai_msg = AIMessage(
        content="",
        tool_calls=[
            {"name": "multiply", "args": {"a": 333, "b": 444}, "id": "call-1", "type": "tool_call"},
        ],
    )
    event = {"type": "values", "data": {"messages": [ai_msg]}}
    renderer.consume_stream_part(event, turn)
    renderer.consume_stream_part(event, turn)

    assert out.getvalue().count("→ tool multiply") == 1
