"""
Reproduce langchain_litellm streaming multi-turn bug (without graphs/llm.py fix).

Symptom:
  - Turn 1 succeeds.
  - Turn 2 fails with:
    litellm.APIConnectionError: DeepseekException - 'str' object has no attribute 'get'

Root cause:
  - Streaming merges AIMessage.content into a malformed list like ["", "answer text"].
  - LiteLLM DeepSeek transformer chokes when that history is sent on the next turn.

Run:
  export LLM_API_KEY="your_key"
  export LLM_API_BASE="https://api.deepseek.com"
  uv run python test/bug.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

from langchain_core.messages import HumanMessage
from langchain_litellm import ChatLiteLLM
from langchain_litellm.chat_models.litellm import _convert_message_to_dict

TURN1_USER = "Hello"
TURN2_USER = "My name is Alex."


def _resolve_credentials() -> tuple[str, str]:
    api_key = os.environ.get("LLM_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
    api_base = os.environ.get("LLM_API_BASE") or os.environ.get("DEEPSEEK_API_BASE") or "https://api.deepseek.com"
    if not api_key:
        print("Missing API key. Set LLM_API_KEY or DEEPSEEK_API_KEY.", file=sys.stderr)
        sys.exit(1)
    return api_key, api_base


def _build_llm(*, streaming: bool, api_key: str, api_base: str) -> ChatLiteLLM:
    # Intentionally use raw ChatLiteLLM (no graphs/llm.py normalization subclass).
    return ChatLiteLLM(
        model="deepseek/deepseek-v4-pro",
        api_key=api_key,
        api_base=api_base,
        streaming=streaming,
        temperature=1.0,
        model_kwargs={"thinking": {"type": "enabled"}},
    )


def _print_assistant_payload(label: str, assistant_message) -> None:
    payload = _convert_message_to_dict(assistant_message)
    print(f"\n=== {label} ===")
    print("AIMessage.content:", repr(assistant_message.content)[:500])
    print("Outbound assistant dict:")
    print(json.dumps(payload, indent=2)[:1200])


async def reproduce_streaming_bug(api_key: str, api_base: str) -> None:
    llm = _build_llm(streaming=True, api_key=api_key, api_base=api_base)

    print("[1/3] Turn 1 (streaming=True)...")
    turn1 = await llm.ainvoke([HumanMessage(content=TURN1_USER)])
    print("Turn 1 OK")
    _print_assistant_payload("Malformed history produced by streaming", turn1)

    history = [HumanMessage(content=TURN1_USER), turn1]
    print("\n[2/3] Turn 2 (streaming=True, reusing turn-1 assistant history)...")
    try:
        await llm.ainvoke(history + [HumanMessage(content=TURN2_USER)])
        print("Turn 2 unexpectedly succeeded.")
    except Exception as error:
        print(f"Turn 2 FAILED: {type(error).__name__}: {error}")


async def control_non_streaming_works(api_key: str, api_base: str) -> None:
    llm = _build_llm(streaming=False, api_key=api_key, api_base=api_base)

    print("\n[3/3] Control: non-streaming multi-turn should work...")
    turn1 = await llm.ainvoke([HumanMessage(content=TURN1_USER)])
    _print_assistant_payload("Non-streaming assistant payload", turn1)

    history = [HumanMessage(content=TURN1_USER), turn1]
    turn2 = await llm.ainvoke(history + [HumanMessage(content=TURN2_USER)])
    preview = str(turn2.content)
    print("Turn 2 OK. Preview:", preview[:120])


async def main() -> None:
    api_key, api_base = _resolve_credentials()
    print("Model: deepseek/deepseek-v4-pro")
    print(f"API base: {api_base}")

    await reproduce_streaming_bug(api_key=api_key, api_base=api_base)
    await control_non_streaming_works(api_key=api_key, api_base=api_base)


if __name__ == "__main__":
    asyncio.run(main())
