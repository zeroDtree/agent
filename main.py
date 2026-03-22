import asyncio

import gnureadline  # noqa: F401 – enables readline history/editing in input()
import hydra
import omegaconf
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from omegaconf import DictConfig

from config.config_class import AutoMode, GraphConfig, LLMConfig, ToolConfig, WorkConfig
from graphs.graph import Graph
from tools import get_all_tools
from utils.logger import LoggerConfig, get_and_create_new_log_dir, get_logger
from utils.preset import preset_messages

# ---------------------------------------------------------------------------
# Config builders
# ---------------------------------------------------------------------------


def _build_configs(cfg: DictConfig) -> tuple[LoggerConfig, LLMConfig, WorkConfig, GraphConfig, ToolConfig]:
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

    # os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost,::1")

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
# Streaming output
# ---------------------------------------------------------------------------


async def _print_stream(events, logger):
    printed_ids: set = set()
    async for event in events:
        messages = event.get("messages") or []
        if not messages:
            continue

        # Collect consecutive AI/tool messages from the tail
        recent: list = []
        for msg in reversed(messages):
            if isinstance(msg, (AIMessage, ToolMessage)):
                recent.append(msg)
            else:
                break

        for msg in reversed(recent):
            msg_id = getattr(msg, "id", None) or hash(str(msg.content))
            if msg_id not in printed_ids:
                msg.pretty_print()
                printed_ids.add(msg_id)


# ---------------------------------------------------------------------------
# Main chat loop
# ---------------------------------------------------------------------------


async def _chat_loop(graph, cfg: DictConfig, logger):
    is_first = True
    while True:
        try:
            input_str = input("You: ")
            messages = (preset_messages if is_first else []) + [HumanMessage(content=input_str)]
            is_first = False

            events = graph.astream(
                input={"messages": messages},
                config={
                    "configurable": {"thread_id": cfg.system.thread_id},
                    "recursion_limit": cfg.system.recursion_limit,
                },
                stream_mode=cfg.system.stream_mode,
            )
            await _print_stream(events, logger)

        except KeyboardInterrupt:
            print("\n\nExiting program")
            break
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            print(f"Error occurred, please try again: {e}")


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

        await _chat_loop(graph, cfg, logger)

    except Exception as e:
        logger.error(f"System startup failed: {e}")
        print(f"System startup failed: {e}")


@hydra.main(config_path="config", config_name="config", version_base="1.3")
def main(cfg: DictConfig):
    asyncio.run(async_main(cfg))


if __name__ == "__main__":
    main()
