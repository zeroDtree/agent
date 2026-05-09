import asyncio
import logging

import gnureadline  # noqa: F401
import hydra
import omegaconf
from langchain_mcp_adapters.client import MultiServerMCPClient
from omegaconf import DictConfig

from chat_cli import run_chat_loop
from chat_cli.logging_setup import quiet_http_client_loggers
from chat_cli.text_output import print_config_block, print_mcp_servers_status, redact_sensitive_mapping
from config.config_class import AutoMode, GraphConfig, LLMConfig, ToolConfig, WorkConfig
from graphs.graph import Graph
from tools import get_all_tools
from utils.logger import LoggerConfig, get_and_create_new_log_dir, get_logger

quiet_http_client_loggers()


def _coerce_bool(value: object, *, default: bool = False) -> bool:
    """Interpret Hydra/OmegaConf or string overrides as bool."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return default


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
        thinking=cfg.llm.get("thinking"),
        show_reasoning=_coerce_bool(omegaconf.OmegaConf.select(cfg.llm, "show_reasoning", default=False)),
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


async def _load_mcp_tools_with_status(mcp_config) -> tuple[list, list[tuple[str, int, str]]]:
    """Load MCP tools per server; return flat tool list and rows for status printing."""
    logger = logging.getLogger(__name__)
    client = MultiServerMCPClient(dict(mcp_config))
    all_tools: list = []
    rows: list[tuple[str, int, str]] = []

    for name in mcp_config:
        try:
            tools = await client.get_tools(server_name=name)
            all_tools.extend(tools)
            rows.append((name, len(tools), "ok"))
        except Exception as e:
            logger.warning("MCP server '%s' unavailable, skipping: %s", name, e)
            rows.append((name, 0, str(e)))

    return all_tools, rows


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


async def async_main(cfg: DictConfig):
    resolved = omegaconf.OmegaConf.to_container(cfg, resolve=True)
    if isinstance(resolved, dict):
        safe = redact_sensitive_mapping(resolved)
    else:
        safe = resolved
    print_config_block("Hydra config", safe)

    log_config, llm_config, work_config, graph_config, tool_config = _build_configs(cfg)
    log_dir = get_and_create_new_log_dir(root=log_config.log_dir, prefix="", suffix="", strftime_format="%Y%m%d")
    logger = get_logger(name=__name__, log_dir=log_dir)

    try:
        mcp_tools, mcp_rows = await _load_mcp_tools_with_status(cfg.mcp)
        print_mcp_servers_status(mcp_rows)
        tools = get_all_tools(work_config=work_config) + mcp_tools
        graph = Graph(
            logger=logger,
            llm_config=llm_config,
            work_config=work_config,
            config=graph_config,
            tool_config=tool_config,
        ).create_graph(need_memory=True, tools=tools)

        await run_chat_loop(
            graph=graph,
            cfg=cfg,
            llm_config=llm_config,
            graph_config=graph_config,
            logger=logger,
            tools=tools,
            work_config=work_config,
        )

    except Exception as e:
        logger.error("System startup failed: %s", e)
        print(f"System startup failed: {e}")


@hydra.main(config_path="config", config_name="config", version_base="1.3")
def main(cfg: DictConfig):
    asyncio.run(async_main(cfg))


if __name__ == "__main__":
    main()
