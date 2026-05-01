from __future__ import annotations

from collections import deque

from ..types import LoreBook, LoreEntry, RuntimeContext, RuntimeEvent, Stage
from .events import RuntimeEventSink
from .filter import LoreFilterStage
from .match import LoreMatcher


class LoreExpander:
    """Expand stage: recursively match/filter new candidates from recursive entries."""

    def __init__(
        self,
        lorebook: LoreBook,
        matcher: LoreMatcher,
        filter_stage: LoreFilterStage,
        sink: RuntimeEventSink,
    ):
        self._lorebook = lorebook
        self._matcher = matcher
        self._filter = filter_stage
        self._sink = sink

    def run_expand(
        self,
        filtered: list[LoreEntry],
        context: RuntimeContext,
        events: list[RuntimeEvent],
        match_scores: dict[str, int],
    ) -> list[LoreEntry]:
        entry_map = {entry.id: entry for entry in self._lorebook.entries if entry.enabled}
        selected = {entry.id: entry for entry in filtered}
        # Queue keeps (entry, depth) where depth=1 is the first recursive expansion layer.
        queue: deque[tuple[LoreEntry, int]] = deque(
            (entry, 1) for entry in filtered if entry.resolved.advanced.recursive
        )
        processed_steps = 0

        while queue and processed_steps < self._lorebook.runtime.max_recursion_steps:
            parent_entry, depth = queue.popleft()
            processed_steps += 1
            nested_context = RuntimeContext(
                request_id=context.request_id,
                session_id=context.session_id,
                role=context.role,
                text=parent_entry.content,
                source_texts=context.source_texts,
                tags=context.tags,
                active_sources=context.active_sources,
                turn_index=context.turn_index,
                seed=context.seed,
            )

            for candidate in entry_map.values():
                if candidate.id in selected:
                    continue
                if (
                    candidate.resolved.advanced.max_recursion_depth
                    and depth > candidate.resolved.advanced.max_recursion_depth
                ):
                    continue
                score, hit = self._matcher.match_hit_score(candidate, nested_context, events)
                if hit:
                    reason = self._filter.filter_reason(candidate, nested_context)
                    if reason is None:
                        selected[candidate.id] = candidate
                        match_scores[candidate.id] = score
                        self._sink.event(
                            events,
                            context,
                            candidate.id,
                            Stage.EXPAND,
                            "matched",
                            "recursive_match",
                            {"step": processed_steps, "depth": depth},
                        )
                        if candidate.resolved.advanced.recursive:
                            queue.append((candidate, depth + 1))

        return list(selected.values())
