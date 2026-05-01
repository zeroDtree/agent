from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from ..types.conversation import MessageType
from ..types.lorebook import InjectionPositionType
from .config import PresetSegmentConfig, PresetSegmentId
from .segments import PresetSegmentAssembler


@dataclass(slots=True)
class _ResolvedInjectedEntry:
    full_entry_id: str
    content: str
    order: int | None
    position_type: InjectionPositionType | None
    message_type: MessageType | None
    depth: int | None


class LoreBookInjectionAssembler:
    """Maps lorebook runtime output to LangChain messages and anchor positions."""

    def __init__(self, segment_config: type[PresetSegmentConfig]) -> None:
        self._segment_config = segment_config

    def _preset_segment_enabled(self, preset_segments_enabled: dict[str, bool], sid: PresetSegmentId) -> bool:
        return preset_segments_enabled.get(sid.value, self._segment_config.default_segments_enabled[sid.value])

    @staticmethod
    def normalize_lorebook_ids(lorebook_ids: list[str] | None) -> list[str]:
        return list(dict.fromkeys(lorebook_ids)) if lorebook_ids else ["coding-default"]

    def resolve_injected_entries(
        self,
        runtime_injected_entries: list[str],
        selected_lorebook_ids: list[str],
        engine_by_lorebook_id: dict,
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
            entry = next((e for e in engine.lorebook.entries if e.id == entry_id), None)
            if entry is None:
                continue
            resolved.append(
                _ResolvedInjectedEntry(
                    full_entry_id=f"{lorebook_id}:{entry_id}",
                    content=entry.content,
                    order=entry.resolved.injection.order,
                    position_type=entry.resolved.injection.position_type,
                    message_type=entry.resolved.injection.message_type,
                    depth=entry.resolved.injection.depth,
                )
            )
        return resolved

    @staticmethod
    def _sort_key_order_then_id(entry: _ResolvedInjectedEntry) -> tuple[int, str]:
        return (entry.order if entry.order is not None else 0, entry.full_entry_id)

    @staticmethod
    def _sort_key_depth_entries(entry: _ResolvedInjectedEntry) -> tuple[int, int, str]:
        """Sort DEPTH entries so higher depth appears first (further from newest message)
        and within the same depth, lower order appears first (higher order is closer to newest).
        """
        depth_val = entry.depth if entry.depth is not None else 0
        order_val = entry.order if entry.order is not None else 0
        return (-depth_val, order_val, entry.full_entry_id)

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
                tool_call_id="lorebook-inline",
                name="lorebook",
            )
        return SystemMessage(content=content)

    def append_injected_messages(
        self, messages: list[BaseMessage], entries: list[_ResolvedInjectedEntry]
    ) -> None:
        for entry in entries:
            if not entry.content.strip():
                continue
            messages.append(self.langchain_message_for_lore_entry(entry.content, entry.message_type))

    def bucket_anchor_entries(
        self,
        resolved_injected_entries: list[_ResolvedInjectedEntry],
    ) -> tuple[
        dict[InjectionPositionType, list[_ResolvedInjectedEntry]],
        list[_ResolvedInjectedEntry],
        list[_ResolvedInjectedEntry],
    ]:
        """Partition entries into anchor buckets, depth-segment entries, and overflow.

        Returns:
            anchor_buckets: keyed by the six static InjectionPositionType anchors.
            depth_entries: entries with position_type DEPTH, sorted by depth+order.
            overflow: entries with unknown/None position_type (appended after all segments).
        """
        anchor_buckets: dict[InjectionPositionType, list[_ResolvedInjectedEntry]] = defaultdict(list)
        depth_entries: list[_ResolvedInjectedEntry] = []
        overflow: list[_ResolvedInjectedEntry] = []
        anchor_positions = self._segment_config.anchor_positions()
        for entry in resolved_injected_entries:
            position_type = entry.position_type
            if position_type == InjectionPositionType.DEPTH:
                depth_entries.append(entry)
                continue
            if position_type is None or position_type not in anchor_positions:
                overflow.append(entry)
                continue
            anchor_buckets[position_type].append(entry)
        for bucket in anchor_buckets.values():
            bucket.sort(key=self._sort_key_order_then_id)
        depth_entries.sort(key=self._sort_key_depth_entries)
        overflow.sort(key=self._sort_key_order_then_id)
        return anchor_buckets, depth_entries, overflow

    def assemble_messages(
        self,
        segment_assembler: PresetSegmentAssembler,
        character_prompt_path: str | None,
        persona_prompt_path: str | None,
        preset_segments_enabled: dict[str, bool],
        preset_segment_order: list[str] | None,
        resolved_injected_entries: list[_ResolvedInjectedEntry],
    ) -> list[BaseMessage]:
        resolved = segment_assembler.resolve_segments(
            character_prompt_path=character_prompt_path,
            persona_prompt_path=persona_prompt_path,
            preset_segments_enabled=preset_segments_enabled,
            preset_segment_order=preset_segment_order,
        )
        anchor_buckets, depth_entries, overflow_entries = self.bucket_anchor_entries(
            resolved_injected_entries,
        )
        cfg = self._segment_config
        messages: list[BaseMessage] = []
        for segment_id in resolved.segment_order:
            if segment_id == PresetSegmentId.DEPTH:
                messages.extend(resolved.segment_messages[segment_id])
                if self._preset_segment_enabled(preset_segments_enabled, PresetSegmentId.DEPTH):
                    self.append_injected_messages(messages, depth_entries)
            else:
                before_pos = cfg.segment_before[segment_id]
                after_pos = cfg.segment_after[segment_id]
                self.append_injected_messages(messages, anchor_buckets[before_pos])
                messages.extend(resolved.segment_messages[segment_id])
                self.append_injected_messages(messages, anchor_buckets[after_pos])
        self.append_injected_messages(messages, overflow_entries)
        return messages
