import asyncio
import logging

from langchain_core.messages import ToolMessage

from graphs.state import State
from graphs.utils import extract_text_from_content_blocks


def get_custom_tool_node(tools=None, logger: logging.Logger = None):
    """
    Create a custom tool node that executes tools and converts MCP tool response
    content from list format to string format for LLM compatibility.
    """
    tool_dict = {tool.name: tool for tool in tools} if tools else {}

    async def custom_tool_node(state: State):
        messages = state.get("messages", [])
        last_message = messages[-1] if messages else None

        if not last_message or not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return {"messages": []}

        async def execute_tool(tool_call):
            tool_name = tool_call.get("name", "")
            tool_args = tool_call.get("args", {})
            tool_call_id = tool_call.get("id", "")

            if tool_name in tool_dict:
                tool = tool_dict[tool_name]
                try:
                    if hasattr(tool, "ainvoke"):
                        tool_result = await tool.ainvoke(tool_args)
                    elif hasattr(tool, "invoke"):
                        tool_result = tool.invoke(tool_args)
                    else:
                        tool_result = tool(**tool_args) if callable(tool) else None

                    content = extract_text_from_content_blocks(tool_result)
                    return ToolMessage(content=content, tool_call_id=tool_call_id, name=tool_name)
                except Exception as e:
                    error_msg = f"Error executing tool {tool_name}: {str(e)}"
                    if logger:
                        logger.error(error_msg)
                    return ToolMessage(content=error_msg, tool_call_id=tool_call_id, name=tool_name)
            else:
                error_msg = f"Tool '{tool_name}' not found"
                if logger:
                    logger.warning(error_msg)
                return ToolMessage(content=error_msg, tool_call_id=tool_call_id, name=tool_name)

        tool_messages = await asyncio.gather(*[execute_tool(tc) for tc in last_message.tool_calls])
        return {"messages": tool_messages}

    return custom_tool_node
