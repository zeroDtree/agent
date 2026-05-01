"""Preset assembly: base segments + lorebook injection → LangChain message list."""

from __future__ import annotations

from pathlib import Path

from ..utils.logger import LoreBookEventLogger
from .builder import PresetBuilder, PresetBuildResult
from .config import PresetSegmentConfig, PresetSegmentId
from .engine_manager import LoreBookEngineManager
from .injection_assembly import LoreBookInjectionAssembler
from .reader import PresetPromptReader
from .segments import PresetSegmentAssembler

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_LOREBOOK_ROOT = _PROJECT_ROOT / "prompts/lorebooks"

_EVENT_LOGGER = LoreBookEventLogger()
_SEGMENT_CONFIG = PresetSegmentConfig
_PROMPT_READER = PresetPromptReader(_PROJECT_ROOT)
_SEGMENT_ASSEMBLER = PresetSegmentAssembler(_SEGMENT_CONFIG, _PROMPT_READER)
_INJECTION_ASSEMBLER = LoreBookInjectionAssembler(_SEGMENT_CONFIG)

# Tests may monkeypatch _DEFAULT_ENGINE_MANAGER; build_preset_result reads it at call time.
_DEFAULT_ENGINE_MANAGER = LoreBookEngineManager(_LOREBOOK_ROOT)
_DEFAULT_PRESET_BUILDER = PresetBuilder(
    _SEGMENT_ASSEMBLER,
    _INJECTION_ASSEMBLER,
    _SEGMENT_CONFIG,
    event_logger=_EVENT_LOGGER,
)

def build_preset_result(
    user_input: str,
    thread_id: str,
    turn_index: int,
    lorebook_ids: list[str] | None = None,
    tags: set[str] | None = None,
    character_prompt_path: str | None = None,
    persona_prompt_path: str | None = None,
    preset_segments_enabled: dict[str, bool] | None = None,
    preset_segment_order: list[str] | None = None,
) -> PresetBuildResult:
    # _DEFAULT_ENGINE_MANAGER is read from this module's namespace at call time,
    # so tests can monkeypatch it on `prompt_manager.preset`.
    return _DEFAULT_PRESET_BUILDER.build(
        user_input=user_input,
        thread_id=thread_id,
        turn_index=turn_index,
        lorebook_ids=lorebook_ids,
        tags=tags,
        character_prompt_path=character_prompt_path,
        persona_prompt_path=persona_prompt_path,
        preset_segments_enabled=preset_segments_enabled,
        preset_segment_order=preset_segment_order,
        engine_manager=_DEFAULT_ENGINE_MANAGER,
    )


__all__ = [
    "LoreBookEngineManager",
    "LoreBookInjectionAssembler",
    "PresetBuildResult",
    "PresetBuilder",
    "PresetPromptReader",
    "PresetSegmentAssembler",
    "PresetSegmentConfig",
    "PresetSegmentId",
    "build_preset_result",
]
