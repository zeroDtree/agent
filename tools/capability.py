from __future__ import annotations

from enum import Enum

from config.sandbox import WorkMode


class ToolCapability(str, Enum):
    RO = "ro"
    RW = "rw"
    RW_PLAN = "rw_plan"
    SHELL_RO = "shell_ro"
    SHELL_RW = "shell_rw"


CAPABILITY_METADATA_KEY = "capability"
NEEDS_NETWORK_METADATA_KEY = "needs_network"

MODE_CAPS: dict[WorkMode, frozenset[ToolCapability]] = {
    WorkMode.RO: frozenset({ToolCapability.RO, ToolCapability.SHELL_RO}),
    WorkMode.SW: frozenset({ToolCapability.RO, ToolCapability.RW, ToolCapability.SHELL_RO}),
    WorkMode.AW: frozenset(
        {
            ToolCapability.RO,
            ToolCapability.RW,
            ToolCapability.SHELL_RO,
            ToolCapability.SHELL_RW,
        }
    ),
    WorkMode.PL: frozenset({ToolCapability.RO, ToolCapability.SHELL_RO, ToolCapability.RW_PLAN}),
}

AUTO_APPROVE_CAPABILITIES = frozenset({ToolCapability.RO, ToolCapability.SHELL_RO})
AUTO_REJECT_CAPABILITIES = frozenset(
    {ToolCapability.RW, ToolCapability.SHELL_RW, ToolCapability.RW_PLAN}
)


def get_tool_capability(tool) -> ToolCapability | None:
    metadata = getattr(tool, "metadata", None) or {}
    raw = metadata.get(CAPABILITY_METADATA_KEY)
    if raw is None:
        return None
    return ToolCapability(str(raw))


def tool_needs_network(tool) -> bool:
    metadata = getattr(tool, "metadata", None) or {}
    return bool(metadata.get(NEEDS_NETWORK_METADATA_KEY, False))


def capability_allowed_in_mode(capability: ToolCapability, work_mode: WorkMode) -> bool:
    return capability in MODE_CAPS[work_mode]
