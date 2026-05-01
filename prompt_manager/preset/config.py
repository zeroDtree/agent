from __future__ import annotations

from enum import StrEnum
from typing import ClassVar

from ..types.lorebook import InjectionPositionType


class PresetSegmentId(StrEnum):
    """Known preset segment identifiers (order matches default segment order)."""

    CORE = "core"
    CHARACTER = "character"
    PERSONA = "persona"
    DEPTH = "depth"


# Anchored segments: core, character, persona only.
# The depth segment has no static before/after anchor; its content is driven by
# position_type=DEPTH entries sorted by the depth+order key within assembly.
_ANCHORED_SEGMENTS: tuple[PresetSegmentId, ...] = (
    PresetSegmentId.CORE,
    PresetSegmentId.CHARACTER,
    PresetSegmentId.PERSONA,
)
_DEFAULT_ENABLED: tuple[bool, ...] = (True, True, False, False)
_BEFORE_POSITIONS: tuple[InjectionPositionType, ...] = (
    InjectionPositionType.BEFORE_CORE,
    InjectionPositionType.BEFORE_CHARACTER,
    InjectionPositionType.BEFORE_PERSONA,
)
_AFTER_POSITIONS: tuple[InjectionPositionType, ...] = (
    InjectionPositionType.AFTER_CORE,
    InjectionPositionType.AFTER_CHARACTER,
    InjectionPositionType.AFTER_PERSONA,
)


class PresetSegmentConfig:
    """Static layout for core / character / persona / depth preset segments."""

    DEFAULT_TAGS: ClassVar[frozenset[str]] = frozenset({"coding", "python"})
    all_ids: ClassVar[tuple[PresetSegmentId, ...]] = tuple(PresetSegmentId)
    default_segments_enabled: ClassVar[dict[str, bool]] = {
        sid.value: enabled for sid, enabled in zip(PresetSegmentId, _DEFAULT_ENABLED, strict=True)
    }
    default_segment_order: ClassVar[tuple[str, ...]] = tuple(m.value for m in PresetSegmentId)
    segment_before: ClassVar[dict[str, InjectionPositionType]] = {
        sid.value: pos for sid, pos in zip(_ANCHORED_SEGMENTS, _BEFORE_POSITIONS, strict=True)
    }
    segment_after: ClassVar[dict[str, InjectionPositionType]] = {
        sid.value: pos for sid, pos in zip(_ANCHORED_SEGMENTS, _AFTER_POSITIONS, strict=True)
    }
    _anchor_positions: ClassVar[frozenset[InjectionPositionType]] = frozenset(
        (*segment_before.values(), *segment_after.values())
    )

    @classmethod
    def anchor_positions(cls) -> frozenset[InjectionPositionType]:
        return cls._anchor_positions
