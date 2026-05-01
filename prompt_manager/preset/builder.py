from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from langchain_core.messages import BaseMessage

from ..runtime import MultiLoreBookRuntimeEngine, RuntimeContext
from ..types import SourceScope
from ..utils.logger import LoreBookEventLogger
from .config import PresetSegmentConfig
from .engine_manager import LoreBookEngineManager
from .injection_assembly import LoreBookInjectionAssembler
from .segments import PresetSegmentAssembler


@dataclass(slots=True)
class PresetBuildResult:
    messages: list[BaseMessage]
    #: ``(full_entry_id, injection.order, injection.depth)``. ``depth`` is only set for
    #: ``position_type == DEPTH`` entries; otherwise ``None``.
    injected_entries_with_order: list[tuple[str, int | None, int | None]]


class PresetBuilder:
    """Runs lorebook runtime and merges injections with base preset segments."""

    def __init__(
        self,
        segment_assembler: PresetSegmentAssembler,
        injection_assembler: LoreBookInjectionAssembler,
        segment_config: type[PresetSegmentConfig],
        engine_manager: LoreBookEngineManager | None = None,
        event_logger: LoreBookEventLogger | None = None,
    ) -> None:
        self._segments = segment_assembler
        self._injection = injection_assembler
        self._segment_config = segment_config
        self._engine_manager = engine_manager
        self._event_logger = event_logger

    def build(
        self,
        user_input: str,
        thread_id: str,
        turn_index: int,
        lorebook_ids: list[str] | None = None,
        tags: set[str] | None = None,
        character_prompt_path: str | None = None,
        persona_prompt_path: str | None = None,
        preset_segments_enabled: dict[str, bool] | None = None,
        preset_segment_order: list[str] | None = None,
        engine_manager: LoreBookEngineManager | None = None,
    ) -> PresetBuildResult:
        runtime_context = RuntimeContext(
            request_id=str(uuid4()),
            session_id=thread_id,
            role="user",
            text=user_input,
            tags=tags or set(self._segment_config.DEFAULT_TAGS),
            active_sources={SourceScope.GLOBAL},
            turn_index=turn_index,
        )
        selected_lorebook_ids = self._injection.normalize_lorebook_ids(lorebook_ids)
        manager = engine_manager or self._engine_manager
        if manager is None:
            raise ValueError("No engine_manager provided at construction or call time.")
        engines = [manager.get_engine(lid) for lid in selected_lorebook_ids]
        runtime_result = MultiLoreBookRuntimeEngine(engines).run(runtime_context)

        if self._event_logger is not None:
            self._event_logger.append_events(runtime_result.events)

        engine_by_id = {engine.lorebook.id: engine for engine in engines}
        resolved = self._injection.resolve_injected_entries(
            runtime_injected_entries=runtime_result.injected_entries,
            selected_lorebook_ids=selected_lorebook_ids,
            engine_by_lorebook_id=engine_by_id,
        )
        injected_entries_with_order = [(e.full_entry_id, e.order, e.depth) for e in resolved]

        segments_enabled = dict(self._segment_config.default_segments_enabled)
        if preset_segments_enabled:
            segments_enabled.update(preset_segments_enabled)

        messages = self._injection.assemble_messages(
            segment_assembler=self._segments,
            character_prompt_path=character_prompt_path,
            persona_prompt_path=persona_prompt_path,
            preset_segments_enabled=segments_enabled,
            preset_segment_order=preset_segment_order,
            resolved_injected_entries=resolved,
        )
        return PresetBuildResult(messages=messages, injected_entries_with_order=injected_entries_with_order)
