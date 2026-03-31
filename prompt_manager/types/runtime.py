"""Runtime activation: context, structured events, and engine result."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .common import _md
from .lorebook import SourceScope, Stage


@dataclass(slots=True)
class RuntimeContext:
    """Single activation request: who is asking, what text to scan, tags, and session state."""

    request_id: str = field(
        metadata=_md("Correlation id for one model request; appears in logs and metrics."),
    )
    session_id: str = field(
        metadata=_md("Stable chat/session id for sticky, cooldown, and probability seeding."),
    )
    role: str = field(
        metadata=_md(
            "Logical speaker role for filter checks (e.g. `assistant`, `user`). Must align with "
            "`EntryFilters.role_*` conventions."
        ),
    )
    text: str = field(
        metadata=_md("Primary text scanned for triggers (often the latest user message or concatenated turn text)."),
    )
    source_texts: dict[SourceScope, str] = field(
        default_factory=dict,
        metadata=_md(
            "Optional extra corpora per scope (character description, persona, etc.) merged into "
            "matching when `active_sources` and `source_scope` allow."
        ),
    )
    tags: set[str] = field(
        default_factory=set,
        metadata=_md(
            "Optional host-provided labels; copied into nested `RuntimeContext` during recursive lorebook runs."
        ),
    )
    active_sources: set[SourceScope] = field(
        default_factory=lambda: {"global"},
        metadata=_md("Which scopes from `source_texts` participate in this activation."),
    )
    outlet_references: set[str] = field(
        default_factory=set,
        metadata=_md("Outlet names referenced by the host template; entries targeting other outlets may be dropped."),
    )
    turn_index: int = field(
        default=0,
        metadata=_md("Monotonic counter per session for delay, sticky, and cooldown semantics."),
    )
    seed: int | None = field(
        default=None,
        metadata=_md("Optional explicit seed for probability checks; overrides derived seeds when set."),
    )


@dataclass(slots=True)
class RuntimeEvent:
    """One JSONL-friendly log line: stage, action, reason, optional entry id and metrics."""

    ts: str = field(
        metadata=_md("ISO-8601 timestamp when the event was emitted."),
    )
    request_id: str = field(
        metadata=_md("Links the event to `RuntimeContext.request_id`."),
    )
    session_id: str = field(
        metadata=_md("Links the event to `RuntimeContext.session_id`."),
    )
    lorebook_id: str = field(
        metadata=_md("Which lorebook produced this event."),
    )
    stage: Stage = field(
        metadata=_md("Pipeline phase: scan, match, filter, sort, or inject."),
    )
    action: str = field(
        metadata=_md("Verb within the stage, e.g. `matched`, `dropped`, `inserted`, `passed`."),
    )
    reason: str = field(
        metadata=_md("Machine-oriented reason code, e.g. `keyword_hit`, `budget_overflow`."),
    )
    entry_id: str | None = field(
        default=None,
        metadata=_md("Affected entry id when applicable; None for book-level events."),
    )
    metrics: dict[str, Any] = field(
        default_factory=dict,
        metadata=_md("Numeric or structured details: token counts, remaining budget, group name, etc."),
    )


@dataclass(slots=True)
class RuntimeResult:
    """Outcome of one engine run: concatenated injection text, ids, drops, and events."""

    injected_prompt: str = field(
        metadata=_md("Final text to prepend or append according to host policy (often joined with newlines)."),
    )
    matched_entries: list[str] = field(
        metadata=_md("Entry ids that satisfied triggers before filtering (order not guaranteed)."),
    )
    injected_entries: list[str] = field(
        metadata=_md("Entry ids whose content was included in `injected_prompt` after budget and outlets."),
    )
    dropped_reasons: dict[str, str] = field(
        metadata=_md("Map of entry id to drop reason when an entry was matched but not injected."),
    )
    events: list[RuntimeEvent] = field(
        metadata=_md("Ordered structured events for JSONL export or debugging."),
    )
