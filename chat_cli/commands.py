from __future__ import annotations

import json
from dataclasses import dataclass

from .runtime_config import list_available_roles, resolve_conversation_path, resolve_role_prompt_path
from .serialization import load_conversation, save_conversation
from .state import ChatSessionState

HELP_TEXT = (
    "Commands:\n"
    "  !tool list                   - list available tools\n"
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
    def __init__(self, state: ChatSessionState, tools: list):
        self.state = state
        self.tools = tools
        self._handlers = {
            "!help": self._handle_help,
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

    async def _handle_tool(self, parts: list[str]) -> None:
        sub = parts[1] if len(parts) > 1 else "list"
        if sub == "list":
            if not self.tools:
                print("(no tools available)")
                return
            for tool in self.tools:
                print(f"  {tool.name}")
            return

        tool_name = sub
        raw_args = parts[2] if len(parts) == 3 else "{}"
        matched = next((tool for tool in self.tools if tool.name == tool_name), None)
        if not matched:
            print(f"Unknown tool: {tool_name}. Use '!tool list' to see available tools.")
            return
        try:
            args = json.loads(raw_args)
            result = await matched.ainvoke(args)
            print(result)
        except Exception as error:
            print(f"Tool call failed: {error}")
