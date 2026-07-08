from typing import Any

from langchain_core.messages import ToolMessage
from langgraph.types import Command

from ...config.config_class import ToolApprovalPolicy, WorkConfig
from ..routing import _policy_violation, _should_auto_reject
from ..state import State
from ..tool_call_format import format_tool_calls_summary, tool_call_field, tool_calls_payload


def _rejection_reason_for_tool_call(
    tool_call: Any,
    *,
    work_config: WorkConfig,
    tool_by_name: dict,
    default_reason: str,
) -> str:
    normalized = {
        "name": tool_call_field(tool_call, "name", ""),
        "args": tool_call_field(tool_call, "args", {}),
        "id": tool_call_field(tool_call, "id", ""),
    }
    violation = _policy_violation(normalized, work_config, tool_by_name)
    if violation is not None:
        return f"Tool execution blocked: {violation}"
    if work_config.tool_approval == ToolApprovalPolicy.UNIVERSAL_REJECT:
        return default_reason
    if work_config.tool_approval == ToolApprovalPolicy.BLACKLIST_REJECT and _should_auto_reject(
        normalized, tool_by_name
    ):
        return default_reason
    return default_reason


def get_human_confirm_node(next_node_for_yes: str, next_node_for_no: str):

    def human_confirm(state: State):
        tool_call_message = state["messages"][-1]
        return _console_confirm(state, tool_call_message, next_node_for_yes, next_node_for_no)

    return human_confirm


def _console_confirm(state: State, tool_call_message, next_node_for_yes: str, next_node_for_no: str):
    summary = format_tool_calls_summary(tool_call_message)
    human_str = input(f"About to execute:\n{summary}\nDo you want to proceed? (yes/no): ")
    if human_str in ["y", "Y", "yes", "Yes", "YES"]:
        return Command(goto=next_node_for_yes)

    tool_messages = [
        ToolMessage(
            content="User rejected execution of this tool call",
            tool_call_id=tool_call_field(tc, "id", ""),
        )
        for tc in tool_calls_payload(tool_call_message)
    ]
    return Command(goto=next_node_for_no, update={"messages": tool_messages})


def get_auto_reject_node(
    next_node: str,
    *,
    work_config: WorkConfig,
    tools: list | None = None,
    rejection_reason: str = "Tool execution was automatically rejected",
):

    tool_by_name = {tool.name: tool for tool in (tools or [])}

    def auto_reject_node(state: State):
        last_message = state["messages"][-1]
        tool_messages = [
            ToolMessage(
                content=_rejection_reason_for_tool_call(
                    tc,
                    work_config=work_config,
                    tool_by_name=tool_by_name,
                    default_reason=rejection_reason,
                ),
                tool_call_id=tool_call_field(tc, "id", ""),
            )
            for tc in tool_calls_payload(last_message)
        ]
        return Command(goto=next_node, update={"messages": tool_messages})

    return auto_reject_node
