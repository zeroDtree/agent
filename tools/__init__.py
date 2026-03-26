from config.config_class import WorkConfig

from .embedding_knowledge_base import search_knowledge_base
from .shell import get_run_shell_command_popen_tool
from .todo_list import get_todo_list_tool


def get_all_tools(work_config: WorkConfig) -> list:
    """Return every local tool ready to use.

    Add new tools here; callers never need to change.
    """
    return [
        get_run_shell_command_popen_tool(work_config=work_config),
        # get_todo_list_tool(),
        search_knowledge_base,
    ]


__all__ = [
    "get_run_shell_command_popen_tool",
    "get_todo_list_tool",
    "search_knowledge_base",
    "get_all_tools",
]
