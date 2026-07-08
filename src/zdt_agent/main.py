import asyncio
import logging
import os

import gnureadline  # noqa: F401
import hydra
import omegaconf
from langchain_mcp_adapters.client import MultiServerMCPClient
from omegaconf import DictConfig

from .chat_cli import run_chat_loop
from .chat_cli.logging_setup import quiet_http_client_loggers
from .chat_cli.text_output import print_config_block, print_mcp_servers_status, redact_sensitive_mapping
from .config.config_class import GraphConfig, LLMConfig, McpToolConfig, ToolApprovalPolicy, WorkConfig
from .config.sandbox import NetworkPolicy, SandboxSettings, WorkMode
from .graphs.graph import Graph
from .paths import config_dir, repo_root, runtime_root
from .tools import build_tool_catalog, tag_mcp_tools
from .utils.logger import LoggerConfig, get_and_create_new_log_dir, get_logger

os.environ["AGENT_REPO_ROOT"] = str(repo_root())
os.environ["AGENT_RUNTIME_ROOT"] = str(runtime_root())

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
) -> tuple[LoggerConfig, LLMConfig, WorkConfig, GraphConfig, McpToolConfig]:
    log_config = LoggerConfig(log_dir=cfg.log.log_dir, log_level=cfg.log.log_level)
    llm_config = LLMConfig(
        model=cfg.llm.model,
        api_base=cfg.llm.get("api_base"),
        api_key=cfg.llm.api_key,
        max_tokens=cfg.llm.max_tokens,
        streaming=cfg.llm.streaming,
        temperature=cfg.llm.temperature,
        presence_penalty=cfg.llm.presence_penalty,
        frequency_penalty=cfg.llm.frequency_penalty,
        thinking=cfg.llm.get("thinking"),
        show_reasoning=_coerce_bool(omegaconf.OmegaConf.select(cfg.llm, "show_reasoning", default=False)),
    )

    network_cfg = cfg.work.get("network", {})
    sandbox_cfg = cfg.work.get("sandbox", {})
    work_config = WorkConfig(
        working_directory=cfg.work.working_directory,
        command_timeout=cfg.work.command_timeout,
        tool_approval=ToolApprovalPolicy(cfg.work.tool_approval),
        work_mode=WorkMode(cfg.work.work_mode),
        network=NetworkPolicy(
            enabled=_coerce_bool(network_cfg.get("enabled", False)),
            allowlist=tuple(network_cfg.get("allowlist", [])),
        ),
        sandbox=SandboxSettings(
            plan_directory=str(sandbox_cfg.get("plan_directory", ".agent/plans")),
            deny_read_paths=tuple(sandbox_cfg.get("deny_read_paths", [".env"])),
        ),
    )
    graph_config = GraphConfig(
        n_max_history=cfg.system.n_max_history,
        thread_id=cfg.system.thread_id,
        recursion_limit=cfg.system.recursion_limit,
        stream_mode=cfg.system.stream_mode,
    )
    mcp_defaults = cfg.mcp_tools.get("tool_defaults", {})
    mcp_tools_cfg = dict(cfg.mcp_tools.get("tools", {}))
    tool_capabilities = {
        name: str(value.get("capability", mcp_defaults.get("capability", "ro")))
        for name, value in mcp_tools_cfg.items()
        if isinstance(value, dict)
    }
    tool_needs_network = {
        name: value.get("needs_network")
        for name, value in mcp_tools_cfg.items()
        if isinstance(value, dict) and "needs_network" in value
    }
    mcp_tool_config = McpToolConfig(
        tool_capabilities=tool_capabilities,
        tool_needs_network=tool_needs_network,
        default_capability=str(mcp_defaults.get("capability", "ro")),
        default_needs_network=_coerce_bool(mcp_defaults.get("needs_network", True)),
    )
    return log_config, llm_config, work_config, graph_config, mcp_tool_config


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

    log_config, llm_config, work_config, graph_config, mcp_tool_config = _build_configs(cfg)
    log_dir = get_and_create_new_log_dir(root=log_config.log_dir, prefix="", suffix="", strftime_format="%Y%m%d")
    logger = get_logger(name=__name__, log_dir=log_dir)

    try:
        mcp_tools, mcp_rows = await _load_mcp_tools_with_status(cfg.mcp)
        mcp_tools = tag_mcp_tools(mcp_tools, mcp_tool_config)
        print_mcp_servers_status(mcp_rows)
        tool_catalog = build_tool_catalog(work_config, graph_config, mcp_tools)
        graph = Graph(
            logger=logger,
            llm_config=llm_config,
            work_config=work_config,
            config=graph_config,
        ).create_graph(need_memory=True, tools=tool_catalog)

        await run_chat_loop(
            graph=graph,
            cfg=cfg,
            llm_config=llm_config,
            graph_config=graph_config,
            logger=logger,
            tool_catalog=tool_catalog,
            work_config=work_config,
        )

    except Exception as e:
        logger.error("System startup failed: %s", e)
        print(f"System startup failed: {e}")


@hydra.main(version_base="1.3", config_path=str(config_dir()), config_name="config")
def main(cfg: DictConfig):
    asyncio.run(async_main(cfg))


if __name__ == "__main__":
    main()
