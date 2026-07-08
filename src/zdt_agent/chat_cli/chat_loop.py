from __future__ import annotations

import asyncio

from langchain_core.messages import HumanMessage
from omegaconf import DictConfig

from ..config.config_class import GraphConfig, LLMConfig, WorkConfig
from .commands import CommandDispatcher
from .message_builder import TurnMessageBuilder
from .renderer import CLIStreamRenderer
from .runtime_config import build_chat_session_state


def graph_run_config(graph_config: GraphConfig) -> dict:
    return {
        "configurable": {"thread_id": graph_config.thread_id},
        "recursion_limit": graph_config.recursion_limit,
    }


def _print_welcome_panel(
    *,
    model_name: str,
    role: str,
    temperature: float,
    work_dir: str,
    work_mode: str,
    network_enabled: bool,
    tool_approval: str,
    stream_hint: str,
) -> None:
    network_state = "on" if network_enabled else "off"
    lines = [
        "MyAgent CLI",
        "",
        f"Model        {model_name}",
        f"Role         {role}",
        f"Temperature  {temperature}",
        f"Work dir     {work_dir}",
        f"Work mode    {work_mode}",
        f"Network      {network_state}",
        f"Approval     {tool_approval}",
        "",
        "Type exit or quit to leave. One line per Enter; paste multi-line as one message is OK.",
        "Use !mode, !network, and !approval to change execution policy.",
        stream_hint,
    ]
    inner = max(len(s) for s in lines)
    rule = "+" + "-" * (inner + 4) + "+"
    print()
    print(rule)
    for line in lines:
        print(f"|  {line:<{inner}}  |")
    print(rule)
    print()


async def run_chat_loop(
    graph,
    cfg: DictConfig,
    llm_config: LLMConfig,
    graph_config: GraphConfig,
    logger,
    tool_catalog: list,
    work_config: WorkConfig,
):
    state = build_chat_session_state(cfg, work_config)
    renderer = CLIStreamRenderer(
        show_reasoning=llm_config.show_reasoning,
        model_name=llm_config.model,
    )
    dispatcher = CommandDispatcher(
        state=state,
        tool_catalog=tool_catalog,
        work_config=work_config,
    )
    message_builder = TurnMessageBuilder(state=state, thread_id=str(graph_config.thread_id))

    stream_hint = "Streaming: on" if llm_config.streaming else "Streaming: off (set llm.streaming=true to enable)"
    if llm_config.show_reasoning:
        stream_hint += "  ·  show_reasoning: on"

    _print_welcome_panel(
        model_name=llm_config.model,
        role=state.current_role,
        temperature=llm_config.temperature,
        work_dir=state.shell_working_directory,
        work_mode=work_config.work_mode.value,
        network_enabled=work_config.network.enabled,
        tool_approval=work_config.tool_approval.value,
        stream_hint=stream_hint,
    )

    async def read_command() -> str:
        return await asyncio.to_thread(input, "> ")

    while True:
        try:
            user_input = await read_command()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting CLI...")
            break

        if not user_input.strip():
            continue
        if user_input.lower() in {"exit", "quit"}:
            print("Exiting CLI...")
            break

        try:
            command_result = await dispatcher.handle(user_input)
        except Exception as error:
            logger.error("Command handling failed: %s", error)
            print(f"Error: {error}")
            continue
        if command_result.handled:
            if command_result.should_exit:
                print("Exiting CLI...")
                break
            continue

        state.turn_index += 1
        turn_tail_messages: list = []
        try:
            messages = message_builder.build_messages(user_input=user_input, turn_index=state.turn_index)
            renderer.reset_for_turn()

            if llm_config.streaming:
                try:
                    async for part in graph.astream(
                        {"messages": messages},
                        config=graph_run_config(graph_config),
                        stream_mode=["messages", "values"],
                        version="v2",
                    ):
                        renderer.consume_stream_part(part, turn_tail_messages)
                finally:
                    renderer.finish_stream_turn()
            else:
                async for event in graph.astream(
                    {"messages": messages},
                    config=graph_run_config(graph_config),
                    stream_mode=graph_config.stream_mode,
                ):
                    renderer.consume_nonstream_event(event, turn_tail_messages)
        except Exception as error:
            logger.error("Error: %s", error)
            print(f"Error: {error}")
            continue

        state.conversation_history.append(HumanMessage(content=user_input))
        state.conversation_history.extend(turn_tail_messages)
