from __future__ import annotations

from unittest.mock import patch

from langchain_core.messages import AIMessage

from zdt_agent.graphs.nodes.confirm_node import _console_confirm
from zdt_agent.graphs.state import State


def test_console_confirm_shows_tool_calls_not_content():
    msg = AIMessage(
        content=[{"type": "thinking", "thinking": "should not appear"}],
        tool_calls=[
            {"name": "multiply", "args": {"a": 333, "b": 444}, "id": "call-1", "type": "tool_call"},
        ],
    )
    captured: list[str] = []

    def fake_input(prompt: str) -> str:
        captured.append(prompt)
        return "no"

    with patch("zdt_agent.graphs.nodes.confirm_node.input", side_effect=fake_input):
        result = _console_confirm(State(messages=[], session_id=None), msg, "my_tools", "chatbot")

    assert len(captured) == 1
    prompt = captured[0]
    assert '→ tool multiply {"a": 333, "b": 444}' in prompt
    assert "thinking" not in prompt
    assert result.goto == "chatbot"
    assert len(result.update["messages"]) == 1
