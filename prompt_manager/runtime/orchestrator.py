from __future__ import annotations

from dataclasses import dataclass

from ..types import LoreEntry, RuntimeContext, RuntimeEvent, RuntimeResult
from .engine import LorebookRuntimeEngine
from .helpers import token_count


@dataclass(slots=True)
class _GlobalCandidate:
    engine: LorebookRuntimeEngine
    entry: LoreEntry
    order: int


class MultiLorebookRuntimeEngine:
    """Run multiple lorebooks, then globally sort/inject one merged result."""

    def __init__(self, engines: list[LorebookRuntimeEngine]):
        self._engines = engines

    def run(self, context: RuntimeContext) -> RuntimeResult:
        if not self._engines:
            return RuntimeResult("", [], [], {}, [])
        if len(self._engines) == 1:
            return self._engines[0].run(context)

        events: list[RuntimeEvent] = []
        matched_entries: list[str] = []
        dropped_reasons: dict[str, str] = {}
        candidates: list[_GlobalCandidate] = []

        for engine in self._engines:
            pre_inject = engine.run_pre_inject(context)
            events.extend(pre_inject.events)
            matched_entries.extend([f"{engine.lorebook.id}:{entry.id}" for entry in pre_inject.matched])
            for entry_id, reason in pre_inject.dropped_reasons.items():
                dropped_reasons[f"{engine.lorebook.id}:{entry_id}"] = reason

            sorted_entries = engine._sorter.run_sort(
                pre_inject.expanded,
                context,
                pre_inject.events,
                pre_inject.match_scores,
            )
            candidates.extend(
                _GlobalCandidate(
                    engine=engine,
                    entry=entry,
                    order=entry.resolved.injection.order,
                )
                for entry in sorted_entries
            )

        candidates.sort(key=lambda item: (item.order, item.engine.lorebook.id, item.entry.id))
        total_budget = sum(engine.lorebook.budget.max_tokens for engine in self._engines)
        remaining_budget = total_budget
        injected_texts: list[str] = []
        injected_entries: list[str] = []

        for candidate in candidates:
            engine = candidate.engine
            entry = candidate.entry
            entry_key = f"{engine.lorebook.id}:{entry.id}"
            body, entry_tokens, truncated = engine._injector.prepare_entry_body(entry, context)
            if body is None:
                dropped_reasons[entry_key] = "entry_budget_overflow"
                engine._sink.event(
                    events,
                    context,
                    entry.id,
                    "inject",
                    "dropped",
                    "entry_budget_overflow",
                    {"entry_tokens": entry_tokens, "entry_budget": entry.resolved.budget.max_tokens},
                )
                continue
            if entry_tokens > remaining_budget:
                dropped_reasons[entry_key] = "budget_overflow"
                engine._sink.event(
                    events,
                    context,
                    entry.id,
                    "inject",
                    "dropped",
                    "budget_overflow",
                    {"entry_tokens": entry_tokens, "remaining_budget": remaining_budget},
                )
                continue
            if entry.resolved.injection.outlet and entry.resolved.injection.outlet not in context.outlet_references:
                dropped_reasons[entry_key] = "outlet_not_referenced"
                engine._sink.event(events, context, entry.id, "inject", "dropped", "outlet_not_referenced")
                continue
            injected_texts.append(body)
            injected_entries.append(entry_key)
            remaining_budget -= token_count(body)
            engine._state.apply_after_injection(entry, context)
            metrics: dict[str, object] = {"entry_tokens": entry_tokens}
            if truncated:
                metrics["truncated"] = True
            engine._sink.event(events, context, entry.id, "inject", "inserted", "inserted", metrics)

        return RuntimeResult(
            injected_prompt="\n\n".join(injected_texts),
            matched_entries=matched_entries,
            injected_entries=injected_entries,
            dropped_reasons=dropped_reasons,
            events=events,
        )
