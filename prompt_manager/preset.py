from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import ClassVar
from uuid import uuid4

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from prompt_manager.builder import build_lorebook
from prompt_manager.loader import load_lorebook
from prompt_manager.logger import LoreBookEventLogger
from prompt_manager.runtime import LoreBookRuntimeEngine, MultiLoreBookRuntimeEngine
from prompt_manager.types import RuntimeContext
from prompt_manager.types.conversation import MessageType
from prompt_manager.types.lorebook import InjectionPositionType

# --- Module paths (tests may monkeypatch _DEFAULT_ENGINE_MANAGER) ---

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_LOREBOOK_ROOT = _PROJECT_ROOT / "prompts/lorebooks"
_EVENT_LOGGER = LoreBookEventLogger()

_LOREBOOK_TOOL_TOOL_CALL_ID = "lorebook-inline"

_DEFAULT_LOREBOOK_ID = "coding-default"
_DEFAULT_CHARACTER_PROMPT_PATHS = ["prompts/chars/main.md"]


class PresetSegmentConfig:
    """Static layout for core / character / persona segments."""

    all_ids: ClassVar[tuple[str, ...]] = ("core", "character", "persona")
    default_segments_enabled: ClassVar[dict[str, bool]] = {
        "core": True,
        "character": True,
        "persona": False,
    }
    default_segment_order: ClassVar[tuple[str, ...]] = ("core", "character", "persona")
    segment_before: ClassVar[dict[str, InjectionPositionType]] = {
        "core": InjectionPositionType.BEFORE_CORE,
        "character": InjectionPositionType.BEFORE_CHARACTER,
        "persona": InjectionPositionType.BEFORE_PERSONA,
    }
    segment_after: ClassVar[dict[str, InjectionPositionType]] = {
        "core": InjectionPositionType.AFTER_CORE,
        "character": InjectionPositionType.AFTER_CHARACTER,
        "persona": InjectionPositionType.AFTER_PERSONA,
    }

    @classmethod
    def anchor_positions(cls) -> frozenset[InjectionPositionType]:
        return frozenset(list(cls.segment_before.values()) + list(cls.segment_after.values()))


_SEGMENT_CONFIG = PresetSegmentConfig


@dataclass(slots=True, frozen=True)
class _ResolvedPresetSegments:
    effective_order: list[str]
    segment_messages: dict[str, list[BaseMessage]]


class PresetPromptReader:
    """Loads preset markdown from the project tree."""

    def __init__(self, project_root: Path) -> None:
        self._root = project_root

    def read_text(self, relative_path: str) -> str:
        return (self._root / relative_path).read_text(encoding="utf-8")

    def read_first_existing(self, relative_paths: list[str]) -> str:
        for path in relative_paths:
            candidate = self._root / path
            if candidate.exists():
                return candidate.read_text(encoding="utf-8")
        raise FileNotFoundError(f"None of the prompt files exist: {relative_paths}")

    def read_character_prompt(self, character_prompt_path: str | None) -> str:
        if character_prompt_path:
            candidate = self._root / character_prompt_path
            if not candidate.exists():
                raise FileNotFoundError(f"Character prompt file not found: {character_prompt_path}")
            return candidate.read_text(encoding="utf-8")
        return self.read_first_existing(list(_DEFAULT_CHARACTER_PROMPT_PATHS))

    def read_persona_prompt(self, persona_prompt_path: str | None) -> str | None:
        if not persona_prompt_path:
            return None
        candidate = self._root / persona_prompt_path
        if not candidate.exists():
            raise FileNotFoundError(f"Persona prompt file not found: {persona_prompt_path}")
        return candidate.read_text(encoding="utf-8")


_PROMPT_READER = PresetPromptReader(_PROJECT_ROOT)


class PresetSegmentAssembler:
    """Validates segment order and builds base preset message lists."""

    def __init__(
        self,
        config: type[PresetSegmentConfig],
        reader: PresetPromptReader,
    ) -> None:
        self._config = config
        self._reader = reader

    def validate_segment_order(
        self,
        order: list[str],
        preset_segments_enabled: dict[str, bool],
    ) -> list[str]:
        if not order:
            raise ValueError("preset_segment_order must be non-empty when base messages are included.")
        seen: set[str] = set()
        for segment_id in order:
            if segment_id not in self._config.all_ids:
                raise ValueError(f"Unknown preset segment id: {segment_id!r}")
            if segment_id in seen:
                raise ValueError(f"Duplicate preset segment id in order: {segment_id!r}")
            seen.add(segment_id)
        for segment_id, enabled in preset_segments_enabled.items():
            if enabled and segment_id not in seen:
                raise ValueError(f"Enabled segment {segment_id!r} is missing from preset_segment_order.")
        return order

    def effective_segment_order(
        self,
        validated_order: list[str],
        preset_segments_enabled: dict[str, bool],
    ) -> list[str]:
        return [sid for sid in validated_order if preset_segments_enabled.get(sid, False)]

    def build_segment_message_lists(
        self,
        character_prompt_path: str | None,
        persona_prompt_path: str | None,
        preset_segments_enabled: dict[str, bool],
    ) -> dict[str, list[BaseMessage]]:
        segments: dict[str, list[BaseMessage]] = {"core": [], "character": [], "persona": []}

        if preset_segments_enabled.get("core", True):
            segments["core"] = [
                SystemMessage(content=self._reader.read_text("prompts/core/system.md")),
                AIMessage(content=self._reader.read_first_existing(["prompts/core/ai-ok1.md"])),
                HumanMessage(content=self._reader.read_text("prompts/core/role_play.md")),
                AIMessage(content=self._reader.read_text("prompts/core/ai-ok2.md")),
            ]

        if preset_segments_enabled.get("character", True):
            segments["character"] = [HumanMessage(content=self._reader.read_character_prompt(character_prompt_path))]

        if preset_segments_enabled.get("persona", False):
            persona_text = self._reader.read_persona_prompt(persona_prompt_path)
            if persona_text is not None and persona_text.strip():
                segments["persona"] = [HumanMessage(content=persona_text)]

        return segments

    def resolve_segments(
        self,
        character_prompt_path: str | None,
        persona_prompt_path: str | None,
        preset_segments_enabled: dict[str, bool],
        preset_segment_order: list[str],
    ) -> _ResolvedPresetSegments:
        validated = self.validate_segment_order(preset_segment_order, preset_segments_enabled)
        effective = self.effective_segment_order(validated, preset_segments_enabled)
        segment_messages = self.build_segment_message_lists(
            character_prompt_path=character_prompt_path,
            persona_prompt_path=persona_prompt_path,
            preset_segments_enabled=preset_segments_enabled,
        )
        return _ResolvedPresetSegments(effective_order=effective, segment_messages=segment_messages)

    def flatten_base_messages(
        self,
        character_prompt_path: str | None,
        persona_prompt_path: str | None,
        preset_segments_enabled: dict[str, bool],
        preset_segment_order: list[str],
    ) -> list[BaseMessage]:
        resolved = self.resolve_segments(
            character_prompt_path=character_prompt_path,
            persona_prompt_path=persona_prompt_path,
            preset_segments_enabled=preset_segments_enabled,
            preset_segment_order=preset_segment_order,
        )
        messages: list[BaseMessage] = []
        for segment_id in resolved.effective_order:
            messages.extend(resolved.segment_messages[segment_id])
        return messages


_SEGMENT_ASSEMBLER = PresetSegmentAssembler(_SEGMENT_CONFIG, _PROMPT_READER)


@dataclass(slots=True)
class _ResolvedInjectedEntry:
    full_entry_id: str
    content: str
    order: int | None
    position: InjectionPositionType | None
    message_type: MessageType | None


class LoreBookInjectionAssembler:
    """Maps lorebook runtime output to LangChain messages and anchor positions."""

    def __init__(self, segment_config: type[PresetSegmentConfig]) -> None:
        self._segment_config = segment_config

    @staticmethod
    def normalize_lorebook_ids(lorebook_ids: list[str] | None) -> list[str]:
        if not lorebook_ids:
            return [_DEFAULT_LOREBOOK_ID]
        unique_ids: list[str] = []
        seen: set[str] = set()
        for lorebook_id in lorebook_ids:
            if lorebook_id not in seen:
                unique_ids.append(lorebook_id)
                seen.add(lorebook_id)
        return unique_ids

    def resolve_injected_entries(
        self,
        runtime_injected_entries: list[str],
        selected_lorebook_ids: list[str],
        engine_by_lorebook_id: dict[str, LoreBookRuntimeEngine],
    ) -> list[_ResolvedInjectedEntry]:
        resolved: list[_ResolvedInjectedEntry] = []
        fallback_lorebook_id = selected_lorebook_ids[0] if selected_lorebook_ids else "unknown"

        for injected_entry in runtime_injected_entries:
            if ":" in injected_entry:
                lorebook_id, entry_id = injected_entry.split(":", 1)
            else:
                lorebook_id = fallback_lorebook_id
                entry_id = injected_entry

            engine = engine_by_lorebook_id.get(lorebook_id)
            if engine is None:
                continue

            entry = next((item for item in engine.lorebook.entries if item.id == entry_id), None)
            if entry is None:
                continue

            resolved.append(
                _ResolvedInjectedEntry(
                    full_entry_id=f"{lorebook_id}:{entry_id}",
                    content=entry.content,
                    order=entry.resolved.injection.order,
                    position=entry.resolved.injection.position,
                    message_type=entry.resolved.injection.message_type,
                )
            )

        return resolved

    @staticmethod
    def langchain_message_for_lore_entry(content: str, message_type: MessageType | None) -> BaseMessage:
        role = message_type or MessageType.SYSTEM
        if role == MessageType.SYSTEM:
            return SystemMessage(content=content)
        if role == MessageType.USER:
            return HumanMessage(content=content)
        if role == MessageType.ASSISTANT:
            return AIMessage(content=content)
        if role == MessageType.TOOL:
            return ToolMessage(
                content=content,
                tool_call_id=_LOREBOOK_TOOL_TOOL_CALL_ID,
                name="lorebook",
            )
        return SystemMessage(content=content)

    def append_injected_messages(self, messages: list[BaseMessage], entries: list[_ResolvedInjectedEntry]) -> None:
        for entry in entries:
            if not entry.content.strip():
                continue
            messages.append(self.langchain_message_for_lore_entry(entry.content, entry.message_type))

    def bucket_anchor_entries(
        self, resolved_injected_entries: list[_ResolvedInjectedEntry]
    ) -> tuple[dict[InjectionPositionType, list[_ResolvedInjectedEntry]], list[_ResolvedInjectedEntry]]:
        anchor_buckets: dict[InjectionPositionType, list[_ResolvedInjectedEntry]] = defaultdict(list)
        overflow: list[_ResolvedInjectedEntry] = []
        anchor_positions = self._segment_config.anchor_positions()
        for entry in resolved_injected_entries:
            position = entry.position
            if position is None or position not in anchor_positions:
                overflow.append(entry)
                continue
            anchor_buckets[position].append(entry)
        return anchor_buckets, overflow

    def assemble_messages(
        self,
        segment_assembler: PresetSegmentAssembler,
        include_base_messages: bool,
        character_prompt_path: str | None,
        persona_prompt_path: str | None,
        preset_segments_enabled: dict[str, bool],
        preset_segment_order: list[str],
        resolved_injected_entries: list[_ResolvedInjectedEntry],
    ) -> list[BaseMessage]:
        anchor_buckets, overflow_entries = self.bucket_anchor_entries(resolved_injected_entries)

        if not include_base_messages:
            messages: list[BaseMessage] = []
            self.append_injected_messages(messages, resolved_injected_entries)
            return messages

        resolved = segment_assembler.resolve_segments(
            character_prompt_path=character_prompt_path,
            persona_prompt_path=persona_prompt_path,
            preset_segments_enabled=preset_segments_enabled,
            preset_segment_order=preset_segment_order,
        )

        cfg = self._segment_config
        messages = []
        for segment_id in resolved.effective_order:
            before_pos = cfg.segment_before[segment_id]
            after_pos = cfg.segment_after[segment_id]
            self.append_injected_messages(messages, anchor_buckets[before_pos])
            messages.extend(resolved.segment_messages[segment_id])
            self.append_injected_messages(messages, anchor_buckets[after_pos])

        self.append_injected_messages(messages, overflow_entries)
        return messages


_INJECTION_ASSEMBLER = LoreBookInjectionAssembler(_SEGMENT_CONFIG)


class LoreBookEngineManager:
    """Caches lorebook runtime engines per lorebook id under a root directory."""

    def __init__(self, lorebook_root: Path) -> None:
        self._lorebook_root = lorebook_root
        self._engines: dict[str, LoreBookRuntimeEngine] = {}

    def clear(self) -> None:
        self._engines.clear()

    def get_engine(self, lorebook_id: str) -> LoreBookRuntimeEngine:
        cached = self._engines.get(lorebook_id)
        if cached is not None:
            return cached

        lorebook_source = self._lorebook_root / lorebook_id
        lorebook_output = lorebook_source / "lorebook.json"
        if not lorebook_output.exists():
            build_lorebook(source=lorebook_source, output=lorebook_output)
        lorebook = load_lorebook(lorebook_output)
        engine = LoreBookRuntimeEngine(lorebook)
        self._engines[lorebook_id] = engine
        return engine


_DEFAULT_ENGINE_MANAGER = LoreBookEngineManager(_LOREBOOK_ROOT)


@dataclass(slots=True)
class PresetBuildResult:
    messages: list[BaseMessage]
    injected_entries_with_order: list[tuple[str, int | None]]


class PresetBuilder:
    """Runs lorebook runtime and merges injections with base preset segments."""

    def __init__(
        self,
        segment_assembler: PresetSegmentAssembler,
        injection_assembler: LoreBookInjectionAssembler,
        segment_config: type[PresetSegmentConfig],
        engine_manager: LoreBookEngineManager | None = None,
    ) -> None:
        self._segments = segment_assembler
        self._injection = injection_assembler
        self._segment_config = segment_config
        self._engine_manager = engine_manager

    def build(
        self,
        user_input: str,
        thread_id: str,
        turn_index: int,
        lorebook_ids: list[str] | None = None,
        tags: set[str] | None = None,
        include_base_messages: bool = True,
        character_prompt_path: str | None = None,
        persona_prompt_path: str | None = None,
        preset_segments_enabled: dict[str, bool] | None = None,
        preset_segment_order: list[str] | None = None,
    ) -> PresetBuildResult:
        runtime_context = RuntimeContext(
            request_id=str(uuid4()),
            session_id=thread_id,
            role="assistant",
            text=user_input,
            tags=tags or {"coding", "python"},
            active_sources={"global"},
            turn_index=turn_index,
        )
        selected_lorebook_ids = self._injection.normalize_lorebook_ids(lorebook_ids)
        manager = self._engine_manager if self._engine_manager is not None else _DEFAULT_ENGINE_MANAGER
        engines = [manager.get_engine(lid) for lid in selected_lorebook_ids]
        runtime_result = MultiLoreBookRuntimeEngine(engines).run(runtime_context)
        _EVENT_LOGGER.append_events(runtime_result.events)

        engine_by_id = {engine.lorebook.id: engine for engine in engines}
        resolved = self._injection.resolve_injected_entries(
            runtime_injected_entries=runtime_result.injected_entries,
            selected_lorebook_ids=selected_lorebook_ids,
            engine_by_lorebook_id=engine_by_id,
        )
        injected_entries_with_order = [(e.full_entry_id, e.order) for e in resolved]

        segments_enabled = dict(self._segment_config.default_segments_enabled)
        if preset_segments_enabled:
            segments_enabled.update(preset_segments_enabled)
        segment_order = (
            list(preset_segment_order)
            if preset_segment_order is not None
            else list(self._segment_config.default_segment_order)
        )

        messages = self._injection.assemble_messages(
            segment_assembler=self._segments,
            include_base_messages=include_base_messages,
            character_prompt_path=character_prompt_path,
            persona_prompt_path=persona_prompt_path,
            preset_segments_enabled=segments_enabled,
            preset_segment_order=segment_order,
            resolved_injected_entries=resolved,
        )
        return PresetBuildResult(messages=messages, injected_entries_with_order=injected_entries_with_order)


_DEFAULT_PRESET_BUILDER = PresetBuilder(_SEGMENT_ASSEMBLER, _INJECTION_ASSEMBLER, _SEGMENT_CONFIG, engine_manager=None)


@lru_cache(maxsize=1)
def get_base_preset_messages() -> list[BaseMessage]:
    """Default base preset messages; computed once per process (lazy, no import-time disk I/O)."""
    return _SEGMENT_ASSEMBLER.flatten_base_messages(
        character_prompt_path=None,
        persona_prompt_path=None,
        preset_segments_enabled=dict(_SEGMENT_CONFIG.default_segments_enabled),
        preset_segment_order=list(_SEGMENT_CONFIG.default_segment_order),
    )


def build_preset_result(
    user_input: str,
    thread_id: str,
    turn_index: int,
    lorebook_ids: list[str] | None = None,
    tags: set[str] | None = None,
    include_base_messages: bool = True,
    character_prompt_path: str | None = None,
    persona_prompt_path: str | None = None,
    preset_segments_enabled: dict[str, bool] | None = None,
    preset_segment_order: list[str] | None = None,
) -> PresetBuildResult:
    return _DEFAULT_PRESET_BUILDER.build(
        user_input=user_input,
        thread_id=thread_id,
        turn_index=turn_index,
        lorebook_ids=lorebook_ids,
        tags=tags,
        include_base_messages=include_base_messages,
        character_prompt_path=character_prompt_path,
        persona_prompt_path=persona_prompt_path,
        preset_segments_enabled=preset_segments_enabled,
        preset_segment_order=preset_segment_order,
    )
