from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.tools import Tool
from langchain_litellm import ChatLiteLLM

from ..config.config_class import LLMConfig


def _text_from_content_block(block: Any) -> str:
    if isinstance(block, str):
        return block
    if isinstance(block, dict):
        block_type = block.get("type")
        if block_type in ("thinking", "redacted_thinking"):
            return ""
        if block_type == "text" or "text" in block:
            return str(block.get("text", ""))
        if "content" in block:
            return str(block["content"])
    return ""


def _normalize_ai_message_content(content: Any) -> str:
    """Collapse malformed streaming content (e.g. ['', 'answer']) to plain text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [_text_from_content_block(block) for block in content]
        return "".join(parts)
    return str(content) if content is not None else ""


def _normalize_message_for_litellm(message: BaseMessage) -> BaseMessage:
    if not isinstance(message, AIMessage):
        return message
    normalized_content = _normalize_ai_message_content(message.content)
    if normalized_content == message.content:
        return message
    return AIMessage(
        content=normalized_content,
        additional_kwargs=message.additional_kwargs,
        tool_calls=message.tool_calls,
        id=message.id,
        response_metadata=getattr(message, "response_metadata", None) or {},
        usage_metadata=getattr(message, "usage_metadata", None),
    )


class _NormalizedChatLiteLLM(ChatLiteLLM):
    """Normalize assistant history before LiteLLM serializes multi-turn messages."""

    def _create_message_dicts(self, messages: list[BaseMessage], stop: list[str] | None):
        normalized = [_normalize_message_for_litellm(m) for m in messages]
        return super()._create_message_dicts(normalized, stop)


def get_llm_model(config: LLMConfig) -> BaseChatModel:
    model_kwargs: dict[str, Any] = {}
    if config.thinking in {"enabled", "disabled"}:
        model_kwargs["thinking"] = {"type": config.thinking}

    kwargs: dict[str, Any] = {
        "model": config.model,
        "api_key": config.api_key,
        "max_tokens": config.max_tokens,
        "streaming": config.streaming,
        "temperature": config.temperature,
        "presence_penalty": config.presence_penalty,
        "frequency_penalty": config.frequency_penalty,
        "model_kwargs": model_kwargs,
    }
    if config.api_base:
        kwargs["api_base"] = config.api_base
    return _NormalizedChatLiteLLM(**kwargs)


def get_llm_with_tools(config: LLMConfig, tools: list[Tool] | None = None):
    llm = get_llm_model(config=config)
    return llm.bind_tools(tools) if tools else llm
