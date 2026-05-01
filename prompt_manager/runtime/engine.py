from __future__ import annotations

from dataclasses import dataclass

from ..types import LogLevel, LoreBook, LoreEntry, RuntimeContext, RuntimeEvent, Stage
from .events import RuntimeEventSink
from .expand import LoreExpander
from .filter import LoreFilterStage
from .inject import LoreInjector
from .match import LoreMatcher
from .session_state import LoreBookSessionState
from .sort import LoreSorter


@dataclass(slots=True)
class PreInjectResult:
    matched: list[LoreEntry]
    expanded: list[LoreEntry]
    match_scores: dict[str, int]
    dropped_reasons: dict[str, str]
    events: list[RuntimeEvent]


class LoreBookRuntimeEngine:
    def __init__(self, lorebook: LoreBook):
        self.lorebook = lorebook
        self._state = LoreBookSessionState(lorebook)
        self._sink = RuntimeEventSink(lorebook)
        self._matcher = LoreMatcher(lorebook, self._state, self._sink)
        self._filter = LoreFilterStage(lorebook, self._state, self._sink)
        self._expander = LoreExpander(lorebook, self._matcher, self._filter, self._sink)
        self._sorter = LoreSorter(self._sink)
        self._injector = LoreInjector()

    def run_pre_inject(self, context: RuntimeContext) -> PreInjectResult:
        events: list[RuntimeEvent] = []

        if not self.lorebook.enabled:
            if self.lorebook.runtime.log_level != LogLevel.OFF:
                self._sink.event(events, context, None, Stage.SCAN, "skipped", "lorebook_disabled")
            return PreInjectResult([], [], {}, {}, events)

        with self._sink.timed_stage(events, context, Stage.SCAN, "scan_started", "scan_completed") as m:
            active_entries = [e for e in self.lorebook.entries if e.enabled]
            m["scanned_entries"] = len(active_entries)

        with self._sink.timed_stage(events, context, Stage.MATCH, "match_started", "match_completed") as m:
            matched, match_scores = self._matcher.run_match(active_entries, context, events)
            m["matched_entries"] = len(matched)

        with self._sink.timed_stage(events, context, Stage.FILTER, "filter_started", "filter_completed") as m:
            filtered, dropped_reasons = self._filter.run_filter(matched, context, events)
            m["passed_entries"] = len(filtered)

        with self._sink.timed_stage(events, context, Stage.EXPAND, "expand_started", "expand_completed") as m:
            expanded = self._expander.run_expand(filtered, context, events, match_scores)
            m["expanded_entries"] = len(expanded)

        return PreInjectResult(matched, expanded, match_scores, dropped_reasons, events)

    # --- Narrow public API for cross-engine access (used by MultiLoreBookRuntimeEngine) ---

    def sort_expanded(
        self,
        entries: list[LoreEntry],
        context: RuntimeContext,
        events: list[RuntimeEvent],
        match_scores: dict[str, int],
    ) -> list[LoreEntry]:
        return self._sorter.run_sort(entries, context, events, match_scores)

    def prepare_entry_body(self, entry: LoreEntry, context: RuntimeContext) -> tuple[str | None, int, bool]:
        return self._injector.prepare_entry_body(entry, context)

    def apply_after_injection(self, entry: LoreEntry, context: RuntimeContext) -> None:
        self._state.apply_after_injection(entry, context)

    def emit_event(
        self,
        events: list[RuntimeEvent],
        context: RuntimeContext,
        entry_id: str | None,
        stage: Stage,
        action: str,
        reason: str,
        metrics: dict | None = None,
    ) -> None:
        self._sink.event(events, context, entry_id, stage, action, reason, metrics)

