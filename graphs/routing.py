import logging

from langgraph.graph import END

from config.config_class import AutoMode, ToolConfig, WorkConfig
from graphs.state import State


def make_chatbot_router(
    work_config: WorkConfig, tool_config: ToolConfig, logger: logging.Logger | None = None
):
    """Return a routing function for the chatbot node's conditional edges."""

    def chatbot_route(state: State):
        try:
            messages = state.get("messages", [])
            if not messages:
                raise ValueError(f"No messages found in state: {state}")

            ai_message = messages[-1]
            if not (hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0):
                return END

            tool_names = [tc.get("name", "unknown") for tc in ai_message.tool_calls]
            if logger:
                logger.info(f"Tool calls detected: {', '.join(tool_names)}")
                logger.info(f"with args: {ai_message.tool_calls}")
                logger.info(f"{work_config.auto_mode}")

            mode = work_config.auto_mode

            if mode == AutoMode.MANUAL:
                return "human_confirm"
            elif mode == AutoMode.UNIVERSAL_REJECT:
                return "auto_reject"
            elif mode == AutoMode.UNIVERSAL_ACCEPT:
                return "my_tools"
            elif mode == AutoMode.BLACKLIST_REJECT:
                for tc in ai_message.tool_calls:
                    if not _is_safe(tc.get("name", ""), tc.get("args", {}), tool_config):
                        return "auto_reject"
                return "human_confirm"
            elif mode == AutoMode.WHITELIST_ACCEPT:
                for tc in ai_message.tool_calls:
                    if not _is_safe(tc.get("name", ""), tc.get("args", {}), tool_config):
                        return "human_confirm"
                return "my_tools"

            return END
        except Exception as e:
            if logger:
                logger.error(f"Routing function execution error: {e}")
            return END

    return chatbot_route


def _is_safe(tool_name: str, args: dict, tool_config: ToolConfig) -> bool:
    if tool_name in ["run_shell_command_popen_tool"]:
        command = args.get("command", "")
        return command.split(" ")[0] in tool_config.safe_shell_commands
    return tool_name in tool_config.safe_tools
