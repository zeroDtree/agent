from __future__ import annotations

from langchain_core.tools import BaseTool

from ..config.config_class import GraphConfig, McpToolConfig, WorkConfig
from .capability import (
    CAPABILITY_METADATA_KEY,
    MODE_CAPS,
    NEEDS_NETWORK_METADATA_KEY,
    ToolCapability,
    capability_allowed_in_mode,
    get_tool_capability,
)
from .embedding_knowledge_base import (
    add_text_to_knowledge_base,
    get_database_debug_info,
    get_knowledge_base_stats,
    list_knowledge_bases,
    search_knowledge_base,
    switch_database_backend,
)
from .fs_read import get_fs_read_tools
from .fs_write import get_fs_write_tools
from .plan import get_plan_tools
from .shell import get_shell_tools


def _tag_tool(tool: BaseTool, capability: ToolCapability, *, needs_network: bool = False) -> BaseTool:
    metadata = dict(tool.metadata or {})
    metadata[CAPABILITY_METADATA_KEY] = capability.value
    metadata[NEEDS_NETWORK_METADATA_KEY] = needs_network
    tool.metadata = metadata
    return tool


def _build_local_tools(work_config: WorkConfig, graph_config: GraphConfig) -> list[BaseTool]:
    tools: list[BaseTool] = []
    tools.extend(get_fs_read_tools(work_config, graph_config))
    tools.extend(get_fs_write_tools(work_config, graph_config))
    tools.extend(get_plan_tools(work_config, graph_config))
    tools.extend(get_shell_tools(work_config, graph_config))

    tools.append(_tag_tool(search_knowledge_base, ToolCapability.RO))
    tools.append(_tag_tool(get_knowledge_base_stats, ToolCapability.RO))
    tools.append(_tag_tool(list_knowledge_bases, ToolCapability.RO))
    tools.append(_tag_tool(get_database_debug_info, ToolCapability.RO))
    tools.append(_tag_tool(add_text_to_knowledge_base, ToolCapability.RW))
    tools.append(_tag_tool(switch_database_backend, ToolCapability.RW))
    return tools


def tag_mcp_tools(tools: list[BaseTool], mcp_tool_config: McpToolConfig) -> list[BaseTool]:
    tagged: list[BaseTool] = []
    for tool in tools:
        capability_name = mcp_tool_config.tool_capabilities.get(
            tool.name,
            mcp_tool_config.default_capability,
        )
        needs_network = mcp_tool_config.tool_needs_network.get(tool.name)
        if needs_network is None:
            needs_network = mcp_tool_config.default_needs_network
        elif isinstance(needs_network, str):
            needs_network = needs_network.strip().lower() in {"1", "true", "yes", "on"}
        tagged.append(
            _tag_tool(
                tool,
                ToolCapability(str(capability_name)),
                needs_network=bool(needs_network),
            )
        )
    return tagged


def build_tool_catalog(
    work_config: WorkConfig,
    graph_config: GraphConfig,
    mcp_tools: list[BaseTool] | None = None,
) -> list[BaseTool]:
    return _build_local_tools(work_config, graph_config) + (mcp_tools or [])


def filter_tools_for_mode(
    tools: list[BaseTool],
    work_config: WorkConfig,
) -> list[BaseTool]:
    allowed = MODE_CAPS[work_config.work_mode]
    return [tool for tool in tools if get_tool_capability(tool) in allowed]


def is_tool_allowed(tool: BaseTool, work_config: WorkConfig) -> bool:
    capability = get_tool_capability(tool)
    if capability is None:
        return False
    return capability_allowed_in_mode(capability, work_config.work_mode)


__all__ = [
    "build_tool_catalog",
    "filter_tools_for_mode",
    "tag_mcp_tools",
    "is_tool_allowed",
    "get_shell_tools",
]
