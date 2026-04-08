from __future__ import annotations

from dataclasses import dataclass

from ..types import LoreBook, LoreEntry, RuntimeContext, RuntimeEvent, RuntimeResult
from .events import RuntimeEventSink
from .expand import LoreExpander
from .filter import LoreFilterStage
from .inject import LoreInjector
from .match import LoreMatcher
from .scan import ActiveEntryScanner
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
        self._scanner = ActiveEntryScanner(lorebook)
        self._matcher = LoreMatcher(lorebook, self._state, self._sink)
        self._filter = LoreFilterStage(lorebook, self._state, self._sink)
        self._expander = LoreExpander(lorebook, self._matcher, self._filter, self._sink)
        self._sorter = LoreSorter(lorebook, self._sink)
        self._injector = LoreInjector(lorebook, self._state, self._sink)

    def run_pre_inject(self, context: RuntimeContext) -> PreInjectResult:
        events: list[RuntimeEvent] = []

        if not self.lorebook.enabled:
            if self.lorebook.runtime.log_level != "off":
                self._sink.event(events, context, None, "scan", "skipped", "lorebook_disabled")
            return PreInjectResult([], [], {}, {}, events)

        scan_t0 = self._sink.stage_started(events, context, "scan", "scan_started")
        active_entries = self._scanner.collect_enabled_entries()
        self._sink.stage_completed(
            events,
            context,
            "scan",
            "scan_completed",
            scan_t0,
            {"scanned_entries": len(active_entries)},
        )

        match_t0 = self._sink.stage_started(events, context, "match", "match_started")
        matched, match_scores = self._matcher.run_match(active_entries, context, events)
        self._sink.stage_completed(
            events,
            context,
            "match",
            "match_completed",
            match_t0,
            {"matched_entries": len(matched)},
        )

        filter_t0 = self._sink.stage_started(events, context, "filter", "filter_started")
        filtered, dropped_reasons = self._filter.run_filter(matched, context, events)
        self._sink.stage_completed(
            events,
            context,
            "filter",
            "filter_completed",
            filter_t0,
            {"passed_entries": len(filtered)},
        )

        expand_t0 = self._sink.stage_started(events, context, "expand", "expand_started")
        expanded = self._expander.run_expand(filtered, context, events, match_scores)
        self._sink.stage_completed(
            events,
            context,
            "expand",
            "expand_completed",
            expand_t0,
            {"expanded_entries": len(expanded)},
        )

        return PreInjectResult(matched, expanded, match_scores, dropped_reasons, events)

    def sort_and_inject(
        self,
        context: RuntimeContext,
        pre_inject: PreInjectResult,
    ) -> RuntimeResult:
        events = pre_inject.events
        dropped_reasons = pre_inject.dropped_reasons
        sort_t0 = self._sink.stage_started(events, context, "sort", "sort_started")
        sorted_entries = self._sorter.run_sort(pre_inject.expanded, context, events, pre_inject.match_scores)
        self._sink.stage_completed(
            events, context, "sort", "sort_completed", sort_t0, {"sorted_entries": len(sorted_entries)}
        )

        overflow_policy = self.lorebook.budget.overflow_policy
        inject_t0 = self._sink.stage_started(events, context, "inject", "inject_started")
        if overflow_policy == "drop_low_priority":
            injected_prompt, injected_entries, dropped_reasons = self._injector.inject_drop_low_priority(
                sorted_entries, context, events, dropped_reasons
            )
        else:
            injected_prompt, injected_entries, dropped_reasons = self._injector.inject_merge_truncate(
                sorted_entries, context, events, dropped_reasons, overflow_policy
            )
        self._sink.stage_completed(
            events, context, "inject", "inject_completed", inject_t0, {"injected_entries": len(injected_entries)}
        )

        return RuntimeResult(
            injected_prompt=injected_prompt,
            matched_entries=[entry.id for entry in pre_inject.matched],
            injected_entries=injected_entries,
            dropped_reasons=dropped_reasons,
            events=events,
        )

    def run(self, context: RuntimeContext) -> RuntimeResult:
        pre_inject = self.run_pre_inject(context)
        return self.sort_and_inject(context, pre_inject)
