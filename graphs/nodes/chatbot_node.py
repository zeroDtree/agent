from typing import cast

from langchain_core.messages import BaseMessage
from langchain_core.tools import BaseTool, Tool

from config.config_class import LLMConfig, WorkConfig
from graphs.llm import get_llm_with_tools
from graphs.state import State
from tools import filter_tools_for_mode


def get_chatbot_node(
    config: LLMConfig,
    work_config: WorkConfig,
    tool_catalog: list[BaseTool],
    max_history: int = 10000,
):

    async def chatbot(state: State):
        messages = _cleanup_old_messages(state["messages"], max_history=max_history)
        active_tools = filter_tools_for_mode(tool_catalog, work_config)
        llm_with_tools = get_llm_with_tools(config=config, tools=cast(list[Tool], active_tools))
        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    return chatbot


def _cleanup_old_messages(messages: list[BaseMessage], max_history: int) -> list[BaseMessage]:
    if len(messages) > max_history:
        return messages[-max_history:]
    return messages
