from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from prompt_manager.preset import build_preset_result

from .state import ChatSessionState
from .text_output import print_lorebook_injections


class TurnMessageBuilder:
    def __init__(self, state: ChatSessionState, thread_id: str) -> None:
        self.state = state
        self.thread_id = thread_id

    def build_messages(self, user_input: str, turn_index: int) -> list:
        preset_result = build_preset_result(
            user_input=user_input,
            thread_id=self.thread_id,
            turn_index=turn_index,
            lorebook_ids=self.state.lorebook_ids,
            character_prompt_path=self.state.current_prompt_path,
            persona_prompt_path=self.state.persona_prompt_path,
            preset_segments_enabled=self.state.preset_segments_enabled,
            preset_segment_order=self.state.preset_segment_order,
        )
        print_lorebook_injections(preset_result.injected_entries_with_order)

        shell_workdir_notice = SystemMessage(
            content=f"Shell session working directory: {self.state.shell_working_directory}"
        )
        messages = (
            preset_result.messages
            + [shell_workdir_notice]
            + self.state.conversation_history
            + [HumanMessage(content=user_input)]
        )
        self.state.last_built_messages = messages
        return messages
