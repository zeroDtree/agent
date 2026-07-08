import logging

from langgraph.graph import END

from ..config.config_class import ToolApprovalPolicy, WorkConfig
from ..tools import is_tool_allowed
from .state import State
from .tool_policy import (
    AUTO_APPROVE_CAPABILITIES,
    AUTO_REJECT_CAPABILITIES,
    get_tool_capability,
    tool_needs_network,
)


def make_chatbot_router(
    work_config: WorkConfig,
    tools: list,
    logger: logging.Logger | None = None,
):
    """Return a routing function for the chatbot node's conditional edges."""
    tool_by_name = {tool.name: tool for tool in tools}

    def chatbot_route(state: State):
        try:
            messages = state.get("messages", [])
            if not messages:
                raise ValueError(f"No messages found in state: {state}")

            ai_message = messages[-1]
            if not (hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0):
                return END

            for tool_call in ai_message.tool_calls:
                violation = _policy_violation(tool_call, work_config, tool_by_name)
                if violation is not None:
                    if logger:
                        logger.warning("Tool policy violation: %s", violation)
                    return "auto_reject"

            policy = work_config.tool_approval

            if policy == ToolApprovalPolicy.MANUAL:
                return "human_confirm"
            if policy == ToolApprovalPolicy.UNIVERSAL_REJECT:
                return "auto_reject"
            if policy == ToolApprovalPolicy.UNIVERSAL_ACCEPT:
                return "my_tools"
            if policy == ToolApprovalPolicy.BLACKLIST_REJECT:
                for tool_call in ai_message.tool_calls:
                    if _should_auto_reject(tool_call, tool_by_name):
                        return "auto_reject"
                return "human_confirm"
            if policy == ToolApprovalPolicy.WHITELIST_ACCEPT:
                for tool_call in ai_message.tool_calls:
                    if not _should_auto_approve(tool_call, tool_by_name):
                        return "human_confirm"
                return "my_tools"

            return END
        except Exception as error:
            if logger:
                logger.error("Routing function execution error: %s", error)
            return END

    return chatbot_route


def _policy_violation(tool_call: dict, work_config: WorkConfig, tool_by_name: dict) -> str | None:
    tool_name = tool_call.get("name", "")
    tool = tool_by_name.get(tool_name)
    if tool is None:
        return f"unknown tool: {tool_name}"
    if not is_tool_allowed(tool, work_config):
        capability = get_tool_capability(tool)
        return f"tool {tool_name} capability {capability} not allowed in mode {work_config.work_mode.value}"
    if tool_needs_network(tool) and not work_config.network.enabled:
        return f"tool {tool_name} requires network but network.enabled is false"
    return None


def _should_auto_approve(tool_call: dict, tool_by_name: dict) -> bool:
    tool = tool_by_name.get(tool_call.get("name", ""))
    if tool is None:
        return False
    capability = get_tool_capability(tool)
    return capability is not None and capability in AUTO_APPROVE_CAPABILITIES


def _should_auto_reject(tool_call: dict, tool_by_name: dict) -> bool:
    tool = tool_by_name.get(tool_call.get("name", ""))
    if tool is None:
        return True
    capability = get_tool_capability(tool)
    return capability is not None and capability in AUTO_REJECT_CAPABILITIES
