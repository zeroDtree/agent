from enum import Enum


class AutoMode(Enum):
    MANUAL = "manual"  # all tools require confirmation
    UNIVERSAL_REJECT = "universal_reject"  # auto-reject all tools
    BLACKLIST_REJECT = "blacklist_reject"  # other tools require confirmation
    WHITELIST_ACCEPT = "whitelist_accept"  # auto-approve safe tools, confirm dangerous tools
    UNIVERSAL_ACCEPT = "universal_accept"  # auto-approve all tools


class LoggerConfig:
    def __init__(self, log_dir: str = "logs", log_level: str = "INFO"):
        self.log_dir = log_dir
        self.log_level = log_level


class LLMConfig:
    def __init__(
        self,
        model_name: str,
        base_url: str,
        api_key: str,
        max_tokens: int = 8192,
        streaming: bool = True,
        temperature: float = 1.0,
        presence_penalty: float = 0.0,
        frequency_penalty: float = 0.0,
    ):
        self.model_name = model_name
        self.base_url = base_url
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.streaming = streaming
        self.temperature = temperature
        self.presence_penalty = presence_penalty
        self.frequency_penalty = frequency_penalty


class WorkConfig:
    def __init__(
        self,
        working_directory: str = ".",
        command_timeout: int = 30,
        auto_mode: AutoMode = AutoMode.MANUAL,
    ):
        self.working_directory = working_directory
        self.command_timeout = command_timeout
        self.auto_mode = auto_mode


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


class ToolConfig:
    def __init__(
        self,
        safe_tools: list[str],
        dangerous_tools: list[str],
        safe_shell_commands: list[str],
        dangerous_shell_commands: list[str],
    ):
        self.safe_tools = safe_tools
        self.dangerous_tools = dangerous_tools
        self.safe_shell_commands = safe_shell_commands
        self.dangerous_shell_commands = dangerous_shell_commands
