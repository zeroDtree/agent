import asyncio
import json
from pathlib import Path

import gnureadline  # noqa: F401
import hydra
import omegaconf
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from omegaconf import DictConfig
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.history import InMemoryHistory

from config.config_class import AutoMode, GraphConfig, LLMConfig, ToolConfig, WorkConfig
from graphs.graph import Graph
from prompt_manager.preset import build_preset_result
from tools import get_all_tools
from utils.logger import LoggerConfig, get_and_create_new_log_dir, get_logger

_PROJECT_ROOT = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Config builders
# ---------------------------------------------------------------------------


def _build_configs(
    cfg: DictConfig,
) -> tuple[LoggerConfig, LLMConfig, WorkConfig, GraphConfig, ToolConfig]:
    log_config = LoggerConfig(log_dir=cfg.log.log_dir, log_level=cfg.log.log_level)
    llm_config = LLMConfig(
        model_name=cfg.llm.model_name,
        base_url=cfg.llm.base_url,
        api_key=cfg.llm.api_key,
        max_tokens=cfg.llm.max_tokens,
        streaming=cfg.llm.streaming,
        temperature=cfg.llm.temperature,
        presence_penalty=cfg.llm.presence_penalty,
        frequency_penalty=cfg.llm.frequency_penalty,
    )
    work_config = WorkConfig(
        working_directory=cfg.work.working_directory,
        command_timeout=cfg.work.command_timeout,
        auto_mode=AutoMode(cfg.work.auto_mode),
    )
    graph_config = GraphConfig(
        n_max_history=cfg.system.n_max_history,
        thread_id=cfg.system.thread_id,
        recursion_limit=cfg.system.recursion_limit,
        stream_mode=cfg.system.stream_mode,
    )
    tool_config = ToolConfig(
        safe_tools=cfg.tool.get("safe_tools", []),
        dangerous_tools=cfg.tool.get("dangerous_tools", []),
        safe_shell_commands=cfg.tool.get("safe_shell_commands", []),
        dangerous_shell_commands=cfg.tool.get("dangerous_shell_commands", []),
    )
    return log_config, llm_config, work_config, graph_config, tool_config


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------


async def _get_mcp_tools(mcp_config) -> list:
    import logging

    logger = logging.getLogger(__name__)
    client = MultiServerMCPClient(dict(mcp_config))
    all_tools: list = []
    for name in mcp_config:
        try:
            tools = await client.get_tools(server_name=name)
            all_tools.extend(tools)
            logger.info(f"MCP server '{name}': loaded {len(tools)} tools")
        except Exception as e:
            logger.warning(f"MCP server '{name}' unavailable, skipping: {e}")
    return all_tools


# ---------------------------------------------------------------------------
# Message helpers (streaming)
# ---------------------------------------------------------------------------


def _message_text(msg: AIMessage | AIMessageChunk | ToolMessage) -> str:
    c = getattr(msg, "content", None)
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        parts: list[str] = []
        for b in c:
            if isinstance(b, dict) and b.get("type") == "text":
                parts.append(str(b.get("text", "")))
            elif isinstance(b, str):
                parts.append(b)
        return "".join(parts)
    return ""


def _tail_ai_tool_messages(messages: list) -> list:
    recent: list = []
    for msg in reversed(messages):
        if isinstance(msg, (AIMessage, ToolMessage)):
            recent.append(msg)
        else:
            break
    return list(reversed(recent))


def _graph_run_config(cfg: DictConfig) -> dict:
    return {
        "configurable": {"thread_id": cfg.system.thread_id},
        "recursion_limit": cfg.system.recursion_limit,
    }


def _resolve_prompt_dir(prompt_dir: str) -> Path:
    return (_PROJECT_ROOT / prompt_dir).resolve()


def _list_available_roles(prompt_dir: Path) -> list[str]:
    if not prompt_dir.exists() or not prompt_dir.is_dir():
        return []
    return sorted(path.stem for path in prompt_dir.glob("*.md"))


def _resolve_role_prompt_path(prompt_dir: Path, role_name: str) -> str:
    return str((prompt_dir / f"{role_name}.md").relative_to(_PROJECT_ROOT))


def _resolve_conversation_dir(cfg: DictConfig) -> Path:
    chat_cfg = cfg.get("chat")
    configured = str(chat_cfg.get("conversation_dir", "data/conversations")) if chat_cfg else "data/conversations"
    conversation_dir = Path(configured).expanduser()
    if not conversation_dir.is_absolute():
        conversation_dir = (_PROJECT_ROOT / conversation_dir).resolve()
    return conversation_dir


def _resolve_conversation_path(raw_path: str, default_dir: Path) -> Path:
    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return candidate
    if candidate.parent != Path("."):
        return candidate
    return default_dir / candidate


# ---------------------------------------------------------------------------
# Main chat loop
# ---------------------------------------------------------------------------


async def chat_loop(graph, cfg, logger, tools: list):
    session = PromptSession(
        history=InMemoryHistory(),
        auto_suggest=AutoSuggestFromHistory(),
    )

    conversation_history: list = []
    last_built_messages: list | None = None
    turn_index = 0
    char_cfg = cfg.get("char")
    default_conversation_dir = _resolve_conversation_dir(cfg)
    lorebook_ids = list(char_cfg.get("lorebook_ids", [])) if char_cfg else []
    prompt_dir = _resolve_prompt_dir(str(char_cfg.get("prompt_dir", "prompts/chars")) if char_cfg else "prompts/chars")
    current_role = str(char_cfg.get("active", "main")) if char_cfg else "main"

    available_roles = _list_available_roles(prompt_dir)
    if current_role not in available_roles and available_roles:
        print(f"Configured role '{current_role}' not found. Falling back to '{available_roles[0]}'.")
        current_role = available_roles[0]
    elif not available_roles:
        print(f"No role prompts found in {prompt_dir}. Falling back to default prompt behavior.")

    current_prompt_path = _resolve_role_prompt_path(prompt_dir, current_role) if available_roles else None

    preset_segments_enabled = None
    preset_segment_order = None
    persona_prompt_path = None
    if char_cfg:
        persona_raw = char_cfg.get("persona_prompt_path")
        persona_prompt_path = str(persona_raw) if persona_raw else None
        preset_cfg = char_cfg.get("preset")
        if preset_cfg is not None:
            preset_plain = omegaconf.OmegaConf.to_container(preset_cfg, resolve=True)
            if isinstance(preset_plain, dict):
                segments_raw = preset_plain.get("segments")
                if isinstance(segments_raw, dict):
                    preset_segments_enabled = {
                        str(key): bool(value["enabled"])
                        for key, value in segments_raw.items()
                        if isinstance(value, dict) and "enabled" in value
                    }
                order_raw = preset_plain.get("segment_order")
                if isinstance(order_raw, list) and order_raw:
                    preset_segment_order = [str(item) for item in order_raw]

    print("Welcome to MyCodex CLI!")
    print(f"Using model: {cfg.llm.model_name}")
    stream_hint = (
        "token streaming on" if cfg.llm.streaming else "token streaming off (set llm.streaming=true for stream)"
    )
    print(f"Type 'exit' to quit. Enter sends; paste multi-line text as one message. ({stream_hint})\n")

    while True:
        try:
            user_input = await session.prompt_async("> ", multiline=False)
            if not user_input.strip():
                continue

            if user_input.lower() in ["exit", "quit"]:
                print("Exiting CLI...")
                break

            if user_input.startswith("!help"):
                print(
                    "Commands:\n"
                    "  !tool list                   - list available tools\n"
                    "  !tool <name> [json_args]     - call a tool directly\n"
                    "  !char list                   - list available character roles\n"
                    "  !char show                   - show active role\n"
                    "  !char set <role>             - switch active role for next turns\n"
                    "  !save <filename>             - save conversation to default history directory\n"
                    "  !load <filename>             - load conversation from default history directory\n"
                    "  !preset                      - print the last built preset sent to the model\n"
                    "  !clear                       - clear conversation history\n"
                    "  !history                     - show conversation history\n"
                    "  exit / quit                  - exit CLI\n"
                )
                continue

            if user_input.startswith("!char"):
                parts = user_input.split(maxsplit=2)
                sub = parts[1] if len(parts) > 1 else "show"
                available_roles = _list_available_roles(prompt_dir)

                if sub == "list":
                    if not available_roles:
                        print(f"(no role prompts found in {prompt_dir})")
                    else:
                        print("Available roles:")
                        for role in available_roles:
                            marker = " (active)" if role == current_role else ""
                            print(f"  {role}{marker}")
                elif sub == "show":
                    print(f"Active role: {current_role}")
                    if current_prompt_path:
                        print(f"Prompt file: {current_prompt_path}")
                elif sub == "set":
                    if len(parts) < 3:
                        print("Usage: !char set <role>")
                    else:
                        target_role = parts[2].strip()
                        if target_role not in available_roles:
                            print(f"Unknown role: {target_role}. Use '!char list' to see available roles.")
                        else:
                            current_role = target_role
                            current_prompt_path = _resolve_role_prompt_path(prompt_dir, current_role)
                            print(f"Active role switched to: {current_role}")
                else:
                    print("Unknown !char command. Use !char list | !char show | !char set <role>.")
                continue

            if user_input.startswith("!save"):
                parts = user_input.split(maxsplit=1)
                if len(parts) < 2:
                    print("Usage: !save <filename>")
                    continue
                raw_path = parts[1].strip()
                save_path = _resolve_conversation_path(raw_path, default_conversation_dir)
                try:
                    save_path.parent.mkdir(parents=True, exist_ok=True)
                    data = [{"type": type(m).__name__, "content": m.content} for m in conversation_history]
                    with save_path.open("w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    print(f"Conversation saved to {save_path} ({len(data)} messages)")
                except Exception as e:
                    print(f"Save failed: {e}")
                continue

            if user_input.startswith("!load"):
                parts = user_input.split(maxsplit=1)
                if len(parts) < 2:
                    print("Usage: !load <filename>")
                    continue
                raw_path = parts[1].strip()
                load_path = _resolve_conversation_path(raw_path, default_conversation_dir)
                if not load_path.exists():
                    print(f"File not found: {load_path}")
                    continue
                try:
                    with load_path.open("r", encoding="utf-8") as f:
                        loaded = json.load(f)
                    type_map = {"HumanMessage": HumanMessage, "AIMessage": AIMessage, "ToolMessage": ToolMessage}
                    for item in loaded:
                        cls = type_map.get(item.get("type"), HumanMessage)
                        conversation_history.append(cls(content=item["content"]))
                    print(f"Loaded {len(loaded)} messages from {load_path}")
                except Exception as e:
                    print(f"Load failed: {e}")
                continue

            if user_input.startswith("!clear"):
                conversation_history.clear()
                print("Conversation history cleared.")
                continue

            if user_input.startswith("!history"):
                if not conversation_history:
                    print("(empty)")
                for i, m in enumerate(conversation_history):
                    role = type(m).__name__.replace("Message", "")
                    content = str(m.content)[:120]
                    print(f"[{i}] {role}: {content}")
                continue

            if user_input.startswith("!preset"):
                if not last_built_messages:
                    print("(no preset has been built yet)")
                    continue
                print("[Last built preset]")
                for i, m in enumerate(last_built_messages, start=1):
                    role = type(m).__name__.replace("Message", "")
                    print(f"\n[{i}] {role}")
                    print(str(getattr(m, "content", "")))
                continue

            if user_input.startswith("!tool"):
                parts = user_input.split(maxsplit=2)
                sub = parts[1] if len(parts) > 1 else "list"
                if sub == "list":
                    if not tools:
                        print("(no tools available)")
                    for t in tools:
                        print(f"  {t.name}")
                else:
                    tool_name = sub
                    raw_args = parts[2] if len(parts) == 3 else "{}"
                    matched = next((t for t in tools if t.name == tool_name), None)
                    if not matched:
                        print(f"Unknown tool: {tool_name}. Use '!tool list' to see available tools.")
                    else:
                        try:
                            args = json.loads(raw_args)
                            result = await matched.ainvoke(args)
                            print(result)
                        except Exception as e:
                            print(f"Tool call failed: {e}")
                continue

            turn_index += 1
            preset_result = build_preset_result(
                user_input=user_input,
                thread_id=str(cfg.system.thread_id),
                turn_index=turn_index,
                lorebook_ids=lorebook_ids,
                character_prompt_path=current_prompt_path,
                persona_prompt_path=persona_prompt_path,
                preset_segments_enabled=preset_segments_enabled,
                preset_segment_order=preset_segment_order,
            )
            if preset_result.injected_entries_with_order:
                print("[LoreBook triggered entries]")
                for index, (entry_id, entry_order, entry_depth) in enumerate(
                    preset_result.injected_entries_with_order, start=1
                ):
                    bits: list[str] = []
                    if entry_order is not None:
                        bits.append(f"order={entry_order}")
                    if entry_depth is not None:
                        bits.append(f"depth={entry_depth}")
                    suffix = f" ({', '.join(bits)})" if bits else ""
                    print(f"  {index}. {entry_id}{suffix}")
            else:
                print("[LoreBook triggered entries]")
                print("  (none)")
            messages = preset_result.messages + conversation_history + [HumanMessage(content=user_input)]
            last_built_messages = messages

            streaming_printed_tool_keys: set = set()
            streaming_appended_history_keys: set = set()
            nonstreaming_emitted_message_keys: set = set()
            streamed_ai = False
            # Keep chronological order: user message for this turn, then model/tool replies.
            turn_tail_messages: list = []

            if cfg.llm.streaming:
                async for part in graph.astream(
                    {"messages": messages},
                    config=_graph_run_config(cfg),
                    stream_mode=["messages", "values"],
                    version="v2",
                ):
                    if part["type"] == "messages":
                        msg, _meta = part["data"]
                        if isinstance(msg, AIMessageChunk):
                            t = _message_text(msg)
                            if t:
                                print(t, end="", flush=True)
                                streamed_ai = True
                        elif isinstance(msg, AIMessage):
                            if not streamed_ai:
                                text = _message_text(msg)
                                if text:
                                    print(text)
                        elif isinstance(msg, ToolMessage):
                            tid = getattr(msg, "id", None) or hash(str(msg.content))
                            if tid not in streaming_printed_tool_keys:
                                print(f"\n[Tool: {msg.name}]\n{msg.content}")
                                streaming_printed_tool_keys.add(tid)
                    elif part["type"] == "values":
                        state = part["data"]
                        msgs = state.get("messages") or []
                        for m in _tail_ai_tool_messages(msgs):
                            mid = getattr(m, "id", None) or hash(str(m.content))
                            if mid in streaming_appended_history_keys:
                                continue
                            turn_tail_messages.append(m)
                            streaming_appended_history_keys.add(mid)
                if streamed_ai:
                    print()
            else:
                async for event in graph.astream(
                    {"messages": messages},
                    config=_graph_run_config(cfg),
                    stream_mode=cfg.system.stream_mode,
                ):
                    msgs = event.get("messages") or []
                    if not msgs:
                        continue
                    for msg in _tail_ai_tool_messages(msgs):
                        msg_id = getattr(msg, "id", None) or hash(str(msg.content))
                        if msg_id not in nonstreaming_emitted_message_keys:
                            print(msg.content)
                            nonstreaming_emitted_message_keys.add(msg_id)
                            turn_tail_messages.append(msg)

            conversation_history.append(HumanMessage(content=user_input))
            conversation_history.extend(turn_tail_messages)

        except KeyboardInterrupt:
            print("\nExiting CLI...")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"Error occurred: {e}")


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


async def async_main(cfg: DictConfig):
    print(omegaconf.OmegaConf.to_yaml(cfg=cfg))

    log_config, llm_config, work_config, graph_config, tool_config = _build_configs(cfg)
    log_dir = get_and_create_new_log_dir(root=log_config.log_dir, prefix="", suffix="", strftime_format="%Y%m%d")
    logger = get_logger(name=__name__, log_dir=log_dir)

    try:
        mcp_tools = await _get_mcp_tools(cfg.mcp)
        print(f"MCP tools ({len(mcp_tools)}): {[t.name for t in mcp_tools]}")
        tools = get_all_tools(work_config=work_config) + mcp_tools
        graph = Graph(
            logger=logger,
            llm_config=llm_config,
            work_config=work_config,
            config=graph_config,
            tool_config=tool_config,
        ).create_graph(need_memory=True, tools=tools)

        await chat_loop(graph, cfg, logger, tools)

    except Exception as e:
        logger.error(f"System startup failed: {e}")
        print(f"System startup failed: {e}")


@hydra.main(config_path="config", config_name="config", version_base="1.3")
def main(cfg: DictConfig):
    asyncio.run(async_main(cfg))


if __name__ == "__main__":
    main()
