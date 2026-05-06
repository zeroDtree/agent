from typing import Any, cast

from langchain_core.language_models import LanguageModelInput
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import Tool
from langchain_deepseek import ChatDeepSeek
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from config.config_class import LLMConfig


def _uses_deepseek_api(config: LLMConfig) -> bool:
    url = (config.base_url or "").lower()
    name = (config.model_name or "").lower()
    return "deepseek" in name or "deepseek" in url


class _ChatDeepSeekReasoningRoundTrip(ChatDeepSeek):
    """Echo `reasoning_content` on outbound requests when it is stored on `AIMessage`.

    DeepSeek thinking mode requires prior reasoning to be sent back after tool calls.
    LangChain's OpenAI-compatible message dict does not copy this field from
    `additional_kwargs`, which triggers HTTP 400 from the API.
    """

    def _get_request_payload(
        self,
        input_: LanguageModelInput,
        *,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        lc_messages = self._convert_input(input_).to_messages()
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)
        msg_dicts = payload.get("messages")
        if msg_dicts is None:
            return payload
        for lc_msg, msg_dict in zip(lc_messages, msg_dicts, strict=True):
            if isinstance(lc_msg, AIMessage) and (
                rc := lc_msg.additional_kwargs.get("reasoning_content")
            ) is not None:
                msg_dict["reasoning_content"] = rc
        return payload


def get_llm_model(config: LLMConfig) -> BaseChatModel:
    if _uses_deepseek_api(config=config):
        api_key = SecretStr(config.api_key) if config.api_key else None
        return cast(
            Any,
            _ChatDeepSeekReasoningRoundTrip(
                model=config.model_name,
                api_key=api_key,
                api_base=config.base_url,
                max_tokens=config.max_tokens,
                streaming=config.streaming,
                temperature=config.temperature,
                presence_penalty=config.presence_penalty,
                frequency_penalty=config.frequency_penalty,
            ),
        )
    _ChatOpenAI = cast(Any, ChatOpenAI)
    return cast(
        BaseChatModel,
        _ChatOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            model=config.model_name,
            max_tokens=config.max_tokens,
            streaming=config.streaming,
            temperature=config.temperature,
            presence_penalty=config.presence_penalty,
            frequency_penalty=config.frequency_penalty,
        ),
    )


def get_llm_with_tools(config: LLMConfig, tools: list[Tool] | None = None):
    llm = get_llm_model(config=config)
    return llm.bind_tools(tools) if tools else llm
