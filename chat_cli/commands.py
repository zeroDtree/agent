from __future__ import annotations

import json
from dataclasses import dataclass

from config.config_class import WorkConfig
from config.sandbox import NetworkPolicy, WorkMode
from tools import filter_tools_for_mode

from .runtime_config import list_available_roles, resolve_conversation_path, resolve_role_prompt_path
from .serialization import load_conversation, save_conversation
from .state import ChatSessionState

HELP_TEXT = (
    "Commands:\n"
    "  !mode                        - show current work mode\n"
    "  !mode ro|sw|aw|pl            - switch work mode\n"
    "  !network                     - show network switch state\n"
    "  !network on|off              - enable/disable outbound network\n"
    "  !tool list                   - list available tools for current mode\n"
    "  !tool <name> [json_args]     - call a tool directly\n"
    "  !char list                   - list available character roles\n"
    "  !char show                   - show active role\n"
    "  !char set <role>             - switch active role for next turns\n"
    "  !save <filename>             - save conversation to default history directory\n"
    "  !load <filename>             - load messages from file and append to current history\n"
    "  !preset                      - print the last built preset sent to the model\n"
    "  !clear                       - clear conversation history\n"
    "  !history                     - show conversation history\n"
    "  exit / quit                  - exit CLI\n"
    "\n"
    "!load does not clear existing messages; run '!clear' first to restore from file only.\n"
    "\n"
    "Tip: pass ++llm.show_reasoning=true to print model reasoning when available.\n"
)


@dataclass
class CommandResult:
    handled: bool
    should_exit: bool = False


class CommandDispatcher:
    def __init__(self, state: ChatSessionState, tool_catalog: list, work_config: WorkConfig):
        self.state = state
        self.tool_catalog = tool_catalog
        self.work_config = work_config
        self._handlers = {
            "!help": self._handle_help,
            "!mode": self._handle_mode,
            "!network": self._handle_network,
            "!char": self._handle_char,
            "!save": self._handle_save,
            "!load": self._handle_load,
            "!clear": self._handle_clear,
            "!history": self._handle_history,
            "!preset": self._handle_preset,
            "!tool": self._handle_tool,
        }

    async def handle(self, user_input: str) -> CommandResult:
        if not user_input.startswith("!"):
            return CommandResult(handled=False)

        parts = user_input.split(maxsplit=2)
        command = parts[0].lower()
        handler = self._handlers.get(command)
        if handler is None:
            print(f"Unknown command: {command}. Use '!help' to see available commands.")
            return CommandResult(handled=True)
        await handler(parts)
        return CommandResult(handled=True)

    async def _handle_help(self, _parts: list[str]) -> None:
        print(HELP_TEXT)

    async def _handle_mode(self, parts: list[str]) -> None:
        work_config = self.state.work_config
        if work_config is None:
            print("Work mode is not available in this session.")
            return
        if len(parts) == 1:
            print(f"Work mode: {work_config.work_mode.value}")
            return
        target = parts[1].strip().lower()
        try:
            new_mode = WorkMode(target)
        except ValueError:
            print("Usage: !mode ro|sw|aw|pl")
            return
        if new_mode == WorkMode.AW and work_config.work_mode != WorkMode.AW:
            confirm = input("AW mode enables read-write shell. Continue? (yes/no): ")
            if confirm.strip().lower() not in {"y", "yes"}:
                print("Mode switch cancelled.")
                return
        work_config.work_mode = new_mode
        print(f"Work mode switched to: {new_mode.value}")
        self._print_mode_summary(work_config)

    async def _handle_network(self, parts: list[str]) -> None:
        work_config = self.state.work_config
        if work_config is None:
            print("Network policy is not available in this session.")
            return
        if len(parts) == 1:
            state = "on" if work_config.network.enabled else "off"
            print(f"Network: {state}")
            return
        target = parts[1].strip().lower()
        if target not in {"on", "off"}:
            print("Usage: !network on|off")
            return
        if target == "on":
            confirm = input("Enabling network allows outbound connections from shell tools. Continue? (yes/no): ")
            if confirm.strip().lower() not in {"y", "yes"}:
                print("Network switch cancelled.")
                return
            work_config.network = NetworkPolicy(
                enabled=True,
                allowlist=work_config.network.allowlist,
            )
            print("Network enabled.")
            return
        work_config.network = NetworkPolicy(
            enabled=False,
            allowlist=work_config.network.allowlist,
        )
        print("Network disabled.")

    def _print_mode_summary(self, work_config) -> None:
        summaries = {
            WorkMode.RO: "read-only tools + read-only shell",
            WorkMode.SW: "read-write tools + read-only shell",
            WorkMode.AW: "read-write tools + read-write shell",
            WorkMode.PL: "plan write tools + read-only shell",
        }
        print(summaries.get(work_config.work_mode, ""))

    async def _handle_char(self, parts: list[str]) -> None:
        sub = parts[1] if len(parts) > 1 else "show"
        available_roles = list_available_roles(self.state.prompt_dir)

        if sub == "list":
            if not available_roles:
                print(f"(no role prompts found in {self.state.prompt_dir})")
                return
            print("Available roles:")
            for role in available_roles:
                marker = " (active)" if role == self.state.current_role else ""
                print(f"  {role}{marker}")
            return

        if sub == "show":
            print(f"Active role: {self.state.current_role}")
            if self.state.current_prompt_path:
                print(f"Prompt file: {self.state.current_prompt_path}")
            return

        if sub == "set":
            if len(parts) < 3:
                print("Usage: !char set <role>")
                return
            target_role = parts[2].strip()
            if target_role not in available_roles:
                print(f"Unknown role: {target_role}. Use '!char list' to see available roles.")
                return
            self.state.current_role = target_role
            self.state.current_prompt_path = resolve_role_prompt_path(self.state.prompt_dir, self.state.current_role)
            print(f"Active role switched to: {self.state.current_role}")
            return

        print("Unknown !char command. Use !char list | !char show | !char set <role>.")

    async def _handle_save(self, parts: list[str]) -> None:
        if len(parts) < 2:
            print("Usage: !save <filename>")
            return
        raw_path = parts[1].strip()
        save_path = resolve_conversation_path(raw_path, self.state.default_conversation_dir)
        try:
            count = save_conversation(save_path, self.state.conversation_history)
            print(f"Conversation saved to {save_path} ({count} messages)")
        except Exception as error:
            print(f"Save failed: {error}")

    async def _handle_load(self, parts: list[str]) -> None:
        if len(parts) < 2:
            print("Usage: !load <filename>")
            return
        raw_path = parts[1].strip()
        load_path = resolve_conversation_path(raw_path, self.state.default_conversation_dir)
        if not load_path.exists():
            print(f"File not found: {load_path}")
            return
        try:
            loaded = load_conversation(load_path)
            self.state.conversation_history.extend(loaded)
            print(f"Loaded {len(loaded)} messages from {load_path}")
        except Exception as error:
            print(f"Load failed: {error}")

    async def _handle_clear(self, _parts: list[str]) -> None:
        self.state.conversation_history.clear()
        print("Conversation history cleared.")

    async def _handle_history(self, _parts: list[str]) -> None:
        if not self.state.conversation_history:
            print("(empty)")
            return
        for idx, message in enumerate(self.state.conversation_history):
            role = type(message).__name__.replace("Message", "")
            content = str(message.content)[:120]
            print(f"[{idx}] {role}: {content}")

    async def _handle_preset(self, _parts: list[str]) -> None:
        if not self.state.last_built_messages:
            print("(no preset has been built yet)")
            return
        print("[Last built preset]")
        for idx, message in enumerate(self.state.last_built_messages, start=1):
            role = type(message).__name__.replace("Message", "")
            print(f"\n[{idx}] {role}")
            print(str(getattr(message, "content", "")))

    def _active_tools(self) -> list:
        work_config = self.state.work_config or self.work_config
        return filter_tools_for_mode(self.tool_catalog, work_config)

    async def _handle_tool(self, parts: list[str]) -> None:
        sub = parts[1] if len(parts) > 1 else "list"
        if sub == "list":
            active_tools = self._active_tools()
            if not active_tools:
                print("(no tools available)")
                return
            for tool in active_tools:
                print(f"  {tool.name}")
            return

        tool_name = sub
        raw_args = parts[2] if len(parts) == 3 else "{}"
        matched = next((tool for tool in self._active_tools() if tool.name == tool_name), None)
        if not matched:
            print(f"Unknown tool: {tool_name}. Use '!tool list' to see available tools.")
            return
        try:
            args = json.loads(raw_args)
            result = await matched.ainvoke(args)
            print(result)
        except Exception as error:
            print(f"Tool call failed: {error}")
