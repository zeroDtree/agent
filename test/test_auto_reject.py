from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.types import Command

from zdt_agent.config.config_class import ToolApprovalPolicy, WorkConfig
from zdt_agent.config.sandbox import NetworkPolicy, WorkMode
from zdt_agent.graphs.nodes.confirm_node import get_auto_reject_node
from zdt_agent.tools.capability import CAPABILITY_METADATA_KEY, NEEDS_NETWORK_METADATA_KEY, ToolCapability


@dataclass
class _FakeTool:
    name: str
    metadata: dict[str, Any] = field(default_factory=dict)


def _network_tool() -> _FakeTool:
    return _FakeTool(
        name="multiply",
        metadata={
            CAPABILITY_METADATA_KEY: ToolCapability.RO.value,
            NEEDS_NETWORK_METADATA_KEY: True,
        },
    )


def test_auto_reject_handles_aimessage_tool_calls():
    work_config = WorkConfig(
        work_mode=WorkMode.RO,
        network=NetworkPolicy(enabled=False),
        tool_approval=ToolApprovalPolicy.UNIVERSAL_ACCEPT,
    )
    node = get_auto_reject_node(
        next_node="chatbot",
        work_config=work_config,
        tools=[_network_tool()],
    )
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "multiply",
                        "args": {"a": 444, "b": 333},
                        "id": "call-1",
                        "type": "tool_call",
                    }
                ],
            )
        ]
    }

    result = node(state)

    assert isinstance(result, Command)
    assert result.goto == "chatbot"
    assert len(result.update["messages"]) == 1
    tool_message = result.update["messages"][0]
    assert isinstance(tool_message, ToolMessage)
    assert tool_message.tool_call_id == "call-1"
    assert "Tool execution blocked:" in tool_message.content
    assert "requires network but network.enabled is false" in tool_message.content


def test_auto_reject_uses_default_reason_for_universal_reject():
    work_config = WorkConfig(
        work_mode=WorkMode.RO,
        network=NetworkPolicy(enabled=True),
        tool_approval=ToolApprovalPolicy.UNIVERSAL_REJECT,
    )
    local_tool = _FakeTool(
        name="read_file",
        metadata={
            CAPABILITY_METADATA_KEY: ToolCapability.RO.value,
            NEEDS_NETWORK_METADATA_KEY: False,
        },
    )
    node = get_auto_reject_node(
        next_node="chatbot",
        work_config=work_config,
        tools=[local_tool],
    )
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[{"name": "read_file", "args": {}, "id": "call-2", "type": "tool_call"}],
            )
        ]
    }

    result = node(state)
    tool_message = result.update["messages"][0]

    assert tool_message.content == "Tool execution was automatically rejected"
