from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI

from config.config_class import LLMConfig


def get_llm_model(config: LLMConfig) -> ChatOpenAI:
    return ChatOpenAI(
        api_key=config.api_key,
        base_url=config.base_url,
        model=config.model_name,
        max_tokens=config.max_tokens,
        streaming=config.streaming,
        temperature=config.temperature,
        presence_penalty=config.presence_penalty,
        frequency_penalty=config.frequency_penalty,
    )


def get_llm_with_tools(config: LLMConfig, tools: list[Tool]):
    llm = get_llm_model(config=config)
    return llm.bind_tools(tools) if tools else llm
