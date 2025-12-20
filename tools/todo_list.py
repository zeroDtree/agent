from enum import Enum

from langchain_core.tools import tool


class EntryStatus(Enum):
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    UNSTARTED = "unstarted"


class Entry:
    def __init__(self, description, status):
        self.description = description
        self.status = status

    def __repr__(self):
        return f"{self.description} - {self.status}"


class TodoList:
    def __init__(self, todo_list: list[str]):
        self.entries = [Entry(description=description, status=EntryStatus.UNSTARTED) for description in todo_list]
        self.cur_idx = 0

    def add_entry(self, entry):
        self.entries.append(entry)

    def get_entries(self):
        return self.entries

    def mark_current_entry_as_completed(self):
        self.entries[self.cur_idx].status = EntryStatus.COMPLETED
        self.cur_idx += 1

    def mark_current_entry_as_cancelled(self):
        self.entries[self.cur_idx].status = EntryStatus.CANCELLED
        self.cur_idx += 1

    def mark_current_entry_as_unstarted(self):
        self.entries[self.cur_idx].status = EntryStatus.UNSTARTED
        self.cur_idx += 1


todo_list = TodoList(todo_list=[])


@tool
def todo_list_tool(action: str = "show", description: str = None) -> str:
    """
    A simplified TodoList tool for agents to create plans and execute tasks sequentially.

    Args:
        action: Available actions:
            - "show": Display all current task statuses
            - "add": Add a new task (requires description)
            - "complete": Mark current task as completed and move to next
            - "cancel": Mark current task as cancelled and move to next
            - "reset": Reset current task to unstarted
            - "next": Get next unprocessed task content (no state change)
            - "clear": Clear all tasks and reset the list

        description: Task description text when adding a task

    Returns:
        Friendly text representation of the current TodoList state
    """

    # Validate action parameter
    valid_actions = {"show", "add", "complete", "cancel", "reset", "next", "clear"}
    if action not in valid_actions:
        return f"Error: Invalid action '{action}'. Valid actions are: {', '.join(sorted(valid_actions))}"

    try:
        if action == "add":
            if not description.strip():
                return "Error: Description is required when adding a task."

            # Create new Entry object instead of passing string directly
            new_entry = Entry(description.strip(), EntryStatus.UNSTARTED)
            todo_list.add_entry(new_entry)
            return f"✓ Added new task: {description.strip()}\n\n" + format_todo()

        elif action == "complete":
            if not _has_current_task():
                return "Error: No current task to complete. All tasks are finished."

            current_task = todo_list.entries[todo_list.cur_idx].description
            todo_list.mark_current_entry_as_completed()
            return f"✓ Completed task: {current_task}\n\n" + format_todo()

        elif action == "cancel":
            if not _has_current_task():
                return "Error: No current task to cancel. All tasks are finished."

            current_task = todo_list.entries[todo_list.cur_idx].description
            todo_list.mark_current_entry_as_cancelled()
            return f"✗ Cancelled task: {current_task}\n\n" + format_todo()

        elif action == "reset":
            if not _has_current_task():
                return "Error: No current task to reset. All tasks are finished."

            current_task = todo_list.entries[todo_list.cur_idx].description
            todo_list.mark_current_entry_as_unstarted()
            return f"↻ Reset task: {current_task}\n\n" + format_todo()

        elif action == "next":
            if _has_current_task():
                current = todo_list.entries[todo_list.cur_idx].description
                return f"→ Next task: {current}"
            else:
                return "✓ All tasks completed!"

        elif action == "clear":
            todo_list.entries.clear()
            todo_list.cur_idx = 0
            return "✓ Cleared all tasks. Todo list is now empty."

        else:  # show
            return format_todo()

    except IndexError as e:
        return f"Error: Index out of range - {str(e)}"
    except Exception as e:
        return f"Error: An unexpected error occurred - {str(e)}"


def format_todo():
    """Format the todo list with enhanced visual indicators and statistics."""
    if not todo_list.entries:
        return "📝 Todo List is empty. Use 'add' action to create tasks."

    text = "📝 Current Todo List:\n"
    text += "=" * 50 + "\n"

    for idx, entry in enumerate(todo_list.get_entries()):
        # Visual indicators for different states
        if idx == todo_list.cur_idx:
            if entry.status == EntryStatus.UNSTARTED:
                prefix = "→ "  # Current task
            else:
                prefix = "→ "  # Current position but task is done
        else:
            prefix = "  "

        # Status icons
        status_icon = {EntryStatus.COMPLETED: "✓", EntryStatus.CANCELLED: "✗", EntryStatus.UNSTARTED: "○"}.get(
            entry.status, "?"
        )

        text += f"{prefix}{idx + 1:2d}. {status_icon} {entry.description} [{entry.status.value}]\n"
    return text


def _has_current_task():
    """Check if there's a current task available to operate on."""
    return todo_list.cur_idx < len(todo_list.entries)


if __name__ == "__main__":
    todo_list = TodoList(todo_list=["Buy groceries", "Finish report", "Call mom"])
    print(todo_list.get_entries())
    todo_list.mark_current_entry_as_completed()
    print(todo_list.get_entries())
    todo_list.mark_current_entry_as_cancelled()
    print(todo_list.get_entries())
    todo_list.mark_current_entry_as_completed()
    print(todo_list.get_entries())
