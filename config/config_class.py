from enum import Enum
from typing import Literal

from config.sandbox import NetworkPolicy, SandboxSettings, WorkMode


class ToolApprovalPolicy(Enum):
    MANUAL = "manual"  # all tools require confirmation
    UNIVERSAL_REJECT = "universal_reject"  # auto-reject all tools
    BLACKLIST_REJECT = "blacklist_reject"  # dangerous capabilities auto-rejected, others confirmed
    WHITELIST_ACCEPT = "whitelist_accept"  # safe capabilities auto-approved, others confirmed
    UNIVERSAL_ACCEPT = "universal_accept"  # auto-approve all tools


class LoggerConfig:
    def __init__(self, log_dir: str = "logs", log_level: str = "INFO"):
        self.log_dir = log_dir
        self.log_level = log_level


class LLMConfig:
    def __init__(
        self,
        model: str,
        api_key: str,
        api_base: str | None = None,
        max_tokens: int = 8192,
        streaming: bool = True,
        temperature: float = 1.0,
        presence_penalty: float = 0.0,
        frequency_penalty: float = 0.0,
        thinking: Literal["enabled", "disabled"] | None = None,
        show_reasoning: bool = False,
    ):
        self.model = model
        self.api_base = api_base
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.streaming = streaming
        self.temperature = temperature
        self.presence_penalty = presence_penalty
        self.frequency_penalty = frequency_penalty
        self.thinking = thinking
        self.show_reasoning = show_reasoning


class WorkConfig:
    def __init__(
        self,
        working_directory: str = ".",
        command_timeout: int = 30,
        tool_approval: ToolApprovalPolicy = ToolApprovalPolicy.MANUAL,
        work_mode: WorkMode = WorkMode.RO,
        network: NetworkPolicy | None = None,
        sandbox: SandboxSettings | None = None,
    ):
        self.working_directory = working_directory
        self.command_timeout = command_timeout
        self.tool_approval = tool_approval
        self.work_mode = work_mode
        self.network = network or NetworkPolicy()
        self.sandbox = sandbox or SandboxSettings()


class GraphConfig:
    def __init__(
        self,
        n_max_history: int = 10000,
        thread_id: str = "1",
        recursion_limit: int = 1000,
        stream_mode: str = "values",
    ):
        self.n_max_history = n_max_history
        self.thread_id = thread_id
        self.recursion_limit = recursion_limit
        self.stream_mode = stream_mode


class McpToolConfig:
    def __init__(
        self,
        tool_capabilities: dict[str, str] | None = None,
        tool_needs_network: dict[str, bool] | None = None,
        default_capability: str = "ro",
        default_needs_network: bool = True,
    ):
        self.tool_capabilities = tool_capabilities or {}
        self.tool_needs_network = tool_needs_network or {}
        self.default_capability = default_capability
        self.default_needs_network = default_needs_network
