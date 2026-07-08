from __future__ import annotations

from langchain_core.messages import AIMessage

from zdt_agent.graphs.tool_call_format import (
    format_tool_call_line,
    format_tool_calls_summary,
    tool_calls_payload,
)


def test_tool_calls_payload_from_aimessage():
    msg = AIMessage(
        content="",
        tool_calls=[
            {"name": "multiply", "args": {"a": 333, "b": 444}, "id": "call-1", "type": "tool_call"},
        ],
    )
    payload = tool_calls_payload(msg)
    assert payload == [{"name": "multiply", "args": {"a": 333, "b": 444}, "id": "call-1"}]


def test_format_tool_call_line():
    line = format_tool_call_line("multiply", {"a": 333, "b": 444})
    assert line == '→ tool multiply {"a": 333, "b": 444}'


def test_format_tool_calls_summary_multiline():
    msg = AIMessage(
        content=[{"type": "thinking", "thinking": "hidden"}],
        tool_calls=[
            {"name": "multiply", "args": {"a": 1, "b": 2}, "id": "c1", "type": "tool_call"},
            {"name": "add", "args": {"a": 3, "b": 4}, "id": "c2", "type": "tool_call"},
        ],
    )
    summary = format_tool_calls_summary(msg)
    assert '→ tool multiply {"a": 1, "b": 2}' in summary
    assert '→ tool add {"a": 3, "b": 4}' in summary
    assert "thinking" not in summary
