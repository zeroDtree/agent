from enum import Enum

from langchain_core.tools import tool


class EntryStatus(Enum):
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    UNSTARTED = "unstarted"


_STATUS_ICON: dict[EntryStatus, str] = {
    EntryStatus.COMPLETED: "✓",
    EntryStatus.CANCELLED: "✗",
    EntryStatus.UNSTARTED: "○",
}


class Entry:
    def __init__(self, description: str, status: EntryStatus = EntryStatus.UNSTARTED):
        self.description = description
        self.status = status

    def __repr__(self) -> str:
        return f"{self.description} - {self.status.value}"


class TodoList:
    def __init__(self, descriptions: list[str] | None = None):
        self.entries: list[Entry] = [Entry(d) for d in (descriptions or [])]
        self.cur_idx: int = 0

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @property
    def current_entry(self) -> Entry | None:
        if self.cur_idx < len(self.entries):
            return self.entries[self.cur_idx]
        return None

    def format(self) -> str:
        if not self.entries:
            return "Todo list is empty. Use 'add' to create tasks."

        lines = ["Current Todo List:", "=" * 50]
        for idx, entry in enumerate(self.entries):
            pointer = "→" if idx == self.cur_idx else " "
            icon = _STATUS_ICON.get(entry.status, "?")
            lines.append(f"{pointer} {idx + 1:2d}. {icon} {entry.description} [{entry.status.value}]")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def add(self, description: str) -> None:
        self.entries.append(Entry(description))

    def _advance(self, status: EntryStatus) -> str:
        """Mark the current entry with *status* and advance the pointer. Returns the entry description."""
        entry = self.current_entry
        if entry is None:
            raise IndexError("No current task — all tasks are finished.")
        entry.status = status
        self.cur_idx += 1
        return entry.description

    def complete(self) -> str:
        return self._advance(EntryStatus.COMPLETED)

    def cancel(self) -> str:
        return self._advance(EntryStatus.CANCELLED)

    def reset_current(self) -> str:
        """Reset the current entry's status to UNSTARTED (does not advance the pointer)."""
        entry = self.current_entry
        if entry is None:
            raise IndexError("No current task — all tasks are finished.")
        entry.status = EntryStatus.UNSTARTED
        return entry.description

    def clear(self) -> None:
        self.entries.clear()
        self.cur_idx = 0


def get_todo_list_tool():
    todo = TodoList()

    @tool
    def todo_list_tool(action: str = "show", description: str = "") -> str:
        """Manage a sequential todo list for planning and executing tasks.

        Args:
            action: One of:
                - "show"     : Display all tasks and their statuses.
                - "add"      : Append a new task (requires description).
                - "complete" : Mark the current task as completed and advance.
                - "cancel"   : Mark the current task as cancelled and advance.
                - "reset"    : Reset the current task's status to unstarted.
                - "next"     : Show the next pending task without changing state.
                - "clear"    : Remove all tasks and reset the list.
            description: Task text — required only for the "add" action.

        Returns:
            A human-readable string describing the result and the updated list.
        """
        valid_actions = {"show", "add", "complete", "cancel", "reset", "next", "clear"}
        if action not in valid_actions:
            return f"Error: invalid action '{action}'. Valid actions: {', '.join(sorted(valid_actions))}"

        try:
            if action == "add":
                text = description.strip() if description else ""
                if not text:
                    return "Error: 'description' is required when using the 'add' action."
                todo.add(text)
                return f"Added task: {text}\n\n{todo.format()}"

            if action == "complete":
                task = todo.complete()
                return f"Completed: {task}\n\n{todo.format()}"

            if action == "cancel":
                task = todo.cancel()
                return f"Cancelled: {task}\n\n{todo.format()}"

            if action == "reset":
                task = todo.reset_current()
                return f"Reset to unstarted: {task}\n\n{todo.format()}"

            if action == "next":
                entry = todo.current_entry
                return f"Next task: {entry.description}" if entry else "All tasks are finished."

            if action == "clear":
                todo.clear()
                return "Cleared all tasks."

            return todo.format()  # "show"

        except IndexError as exc:
            return f"Error: {exc}"
        except Exception as exc:
            return f"Error: {exc}"

    return todo_list_tool


if __name__ == "__main__":
    tl = TodoList(descriptions=["Buy groceries", "Finish report", "Call mom"])
    print(tl.format())
    print("complete:", tl.complete())
    print("cancel:", tl.cancel())
    print("complete:", tl.complete())
    print(tl.format())
