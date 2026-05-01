from __future__ import annotations

from dataclasses import dataclass

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from .config import PresetSegmentConfig, PresetSegmentId
from .reader import PresetPromptReader


@dataclass(slots=True, frozen=True)
class _ResolvedPresetSegments:
    """segment_order: layout walk (default from config, or CLI/API override list).

    Whether a segment loads preset bodies is ``preset_segments_enabled``; disabled
    ids still appear here but map to empty lists in ``segment_messages``.
    """

    segment_order: list[str]
    segment_messages: dict[str, list[BaseMessage]]


class PresetSegmentAssembler:
    """Builds preset segment message lists from ``PresetSegmentConfig`` layout."""

    def __init__(self, config: type[PresetSegmentConfig], reader: PresetPromptReader) -> None:
        self._config = config
        self._reader = reader

    def _segment_enabled(self, preset_segments_enabled: dict[str, bool], sid: PresetSegmentId) -> bool:
        return preset_segments_enabled.get(sid.value, self._config.default_segments_enabled[sid.value])

    def build_segment_message_lists(
        self,
        character_prompt_path: str | None,
        persona_prompt_path: str | None,
        preset_segments_enabled: dict[str, bool],
    ) -> dict[str, list[BaseMessage]]:
        segments: dict[str, list[BaseMessage]] = {sid.value: [] for sid in self._config.all_ids}

        if self._segment_enabled(preset_segments_enabled, PresetSegmentId.CORE):
            segments[PresetSegmentId.CORE.value] = [
                SystemMessage(content=self._reader.read_text("prompts/core/system.md")),
                AIMessage(content=self._reader.read_first_existing(["prompts/core/ai-ok1.md"])),
                HumanMessage(content=self._reader.read_text("prompts/core/role_play.md")),
                AIMessage(content=self._reader.read_text("prompts/core/ai-ok2.md")),
            ]

        if self._segment_enabled(preset_segments_enabled, PresetSegmentId.CHARACTER):
            segments[PresetSegmentId.CHARACTER.value] = [
                HumanMessage(content=self._reader.read_character_prompt(character_prompt_path))
            ]

        if self._segment_enabled(preset_segments_enabled, PresetSegmentId.PERSONA):
            persona_text = self._reader.read_persona_prompt(persona_prompt_path)
            if persona_text is not None and persona_text.strip():
                segments[PresetSegmentId.PERSONA.value] = [HumanMessage(content=persona_text)]

        return segments

    def resolve_segments(
        self,
        character_prompt_path: str | None,
        persona_prompt_path: str | None,
        preset_segments_enabled: dict[str, bool],
        preset_segment_order: list[str] | None = None,
    ) -> _ResolvedPresetSegments:
        segment_order = list(preset_segment_order) if preset_segment_order else list(self._config.default_segment_order)
        segment_messages = self.build_segment_message_lists(
            character_prompt_path=character_prompt_path,
            persona_prompt_path=persona_prompt_path,
            preset_segments_enabled=preset_segments_enabled,
        )
        return _ResolvedPresetSegments(segment_order=segment_order, segment_messages=segment_messages)
