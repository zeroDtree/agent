from langchain_core.messages import BaseMessage
from langchain_core.tools import Tool

from config.config_class import LLMConfig
from graphs.llm import get_llm_with_tools
from graphs.state import State


def get_chatbot_node(config: LLMConfig, tools: list[Tool] = None, max_history: int = 10000):

    async def chatbot(state: State):
        messages = _cleanup_old_messages(state["messages"], max_history=max_history)
        llm_with_tools = get_llm_with_tools(config=config, tools=tools)
        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    return chatbot


def _cleanup_old_messages(messages: list[BaseMessage], max_history: int) -> list[BaseMessage]:
    if len(messages) > max_history:
        return messages[-max_history:]
    return messages
