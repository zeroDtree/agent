from langchain_core.messages import ToolMessage
from langgraph.types import Command

from graphs.state import State


def get_human_confirm_node(next_node_for_yes: str, next_node_for_no: str):

    def human_confirm(state: State):
        tool_call_message = state["messages"][-1]
        return _console_confirm(state, tool_call_message, next_node_for_yes, next_node_for_no)

    return human_confirm


def _console_confirm(state: State, tool_call_message, next_node_for_yes: str, next_node_for_no: str):
    human_str = input(f"About to execute {tool_call_message.content},\nDo you want to proceed? (yes/no): ")
    if human_str in ["y", "Y", "yes", "Yes", "YES"]:
        return Command(goto=next_node_for_yes)

    tool_messages = [
        ToolMessage(content="User rejected execution of this tool call", tool_call_id=tc["id"])
        for tc in tool_call_message.tool_calls
    ]
    return Command(goto=next_node_for_no, update={"messages": tool_messages})


def get_auto_reject_node(next_node: str, rejection_reason: str = "Tool execution was automatically rejected"):

    def auto_reject_node(state: State):
        tool_messages = [
            ToolMessage(content=rejection_reason, tool_call_id=tc["id"])
            for tc in state["messages"][-1].get("tool_calls", [])
        ]
        return Command(goto=next_node, update={"messages": tool_messages})

    return auto_reject_node
