from .shell import get_run_shell_command_popen_tool  # type: ignore
from .todo_list import get_todo_list_tool  # type: ignore
from .embedding_knowledge_base import search_knowledge_base  # type: ignore

from config.config_class import WorkConfig


def get_all_tools(work_config: WorkConfig) -> list:
    """Return every local tool ready to use.

    Add new tools here; callers never need to change.
    """
    return [
        get_run_shell_command_popen_tool(work_config=work_config),
        get_todo_list_tool(),
        search_knowledge_base,
    ]


__all__ = [
    "get_run_shell_command_popen_tool",
    "get_todo_list_tool",
    "search_knowledge_base",
    "get_all_tools",
]
