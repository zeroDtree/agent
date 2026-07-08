"""Runtime activation: context, structured events, and engine result."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .lorebook import SourceScope


class Stage(StrEnum):
    """Pipeline stage for structured logging (scan → match → filter → expand → sort → inject)."""

    SCAN = "scan"
    MATCH = "match"
    FILTER = "filter"
    EXPAND = "expand"
    SORT = "sort"
    INJECT = "inject"


@dataclass(slots=True)
class RuntimeContext:
    """Single activation request: who is asking, what text to scan, tags, and session state."""

    request_id: str
    session_id: str
    role: str
    text: str
    source_texts: dict[SourceScope, str] = field(default_factory=dict)
    tags: set[str] = field(default_factory=set)
    active_sources: set[SourceScope] = field(default_factory=lambda: {SourceScope.GLOBAL})
    turn_index: int = 0
    seed: int | None = None


@dataclass(slots=True)
class RuntimeEvent:
    """One JSONL-friendly log line: stage, action, reason, optional entry id and metrics."""

    ts: str
    request_id: str
    session_id: str
    lorebook_id: str
    stage: Stage
    action: str
    reason: str
    entry_id: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RuntimeResult:
    """Outcome of one engine run: concatenated injection text, ids, drops, and events."""

    injected_prompt: str
    matched_entries: list[str]
    injected_entries: list[str]
    dropped_reasons: dict[str, str]
    events: list[RuntimeEvent]
