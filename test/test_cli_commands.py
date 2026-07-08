from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from zdt_agent.chat_cli.commands import CommandDispatcher
from zdt_agent.chat_cli.state import ChatSessionState
from zdt_agent.config.config_class import ToolApprovalPolicy, WorkConfig
from zdt_agent.config.sandbox import NetworkPolicy, WorkMode


@pytest.fixture
def dispatcher():
    work_config = WorkConfig(
        work_mode=WorkMode.RO,
        network=NetworkPolicy(enabled=False),
        tool_approval=ToolApprovalPolicy.MANUAL,
    )
    state = ChatSessionState(
        work_config=work_config,
        prompt_dir=Path("."),
        current_role="main",
        default_conversation_dir=Path("data/conversations"),
        shell_working_directory=".",
    )
    return CommandDispatcher(state=state, tool_catalog=[], work_config=work_config)


def test_mode_list_marks_active(dispatcher, capsys):
    asyncio.run(dispatcher.handle("!mode list"))
    output = capsys.readouterr().out
    assert "Available work modes:" in output
    assert "ro (active)" in output


def test_network_list_marks_active(dispatcher, capsys):
    asyncio.run(dispatcher.handle("!network list"))
    output = capsys.readouterr().out
    assert "Network switch options:" in output
    assert "off (active)" in output


def test_approval_list_marks_active(dispatcher, capsys):
    asyncio.run(dispatcher.handle("!approval list"))
    output = capsys.readouterr().out
    assert "Available approval policies:" in output
    assert "manual (active)" in output
