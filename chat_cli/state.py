from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ChatSessionState:
    conversation_history: list = field(default_factory=list)
    last_built_messages: list | None = None
    turn_index: int = 0
    prompt_dir: Path = field(default_factory=Path)
    default_conversation_dir: Path = field(default_factory=Path)
    current_role: str = "main"
    current_prompt_path: str | None = None
    shell_working_directory: str = "."
    lorebook_ids: list[str] = field(default_factory=list)
    persona_prompt_path: str | None = None
    preset_segments_enabled: dict[str, bool] | None = None
    preset_segment_order: list[str] | None = None
