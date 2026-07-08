from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..types import LoreEntry, RuntimeContext, RuntimeEvent, RuntimeResult, Stage
from .engine import LoreBookRuntimeEngine


def inject_budgeted(
    entries: list[LoreEntry],
    context: RuntimeContext,
    events: list[RuntimeEvent],
    dropped_reasons: dict[str, str],
    remaining_budget: int,
    entry_key: Callable[[LoreEntry], str],
    prepare_body: Callable[[LoreEntry, RuntimeContext], tuple[str | None, int, bool]],
    on_success: Callable[[LoreEntry, str, int, bool], None],
    on_drop: Callable[[str, str, dict], None],
) -> tuple[list[str], list[str], dict[str, str]]:
    """Core budgeted-injection loop shared by single-book and multi-book paths.

    Returns (injected_texts, injected_entry_keys, dropped_reasons).
    """
    injected_texts: list[str] = []
    injected_entry_keys: list[str] = []

    for entry in entries:
        key = entry_key(entry)
        body, entry_tokens, truncated = prepare_body(entry, context)
        if body is None:
            dropped_reasons[key] = "entry_budget_overflow"
            on_drop(
                key,
                "entry_budget_overflow",
                {"entry_tokens": entry_tokens, "entry_budget": entry.resolved.budget.max_tokens},
            )
            continue
        if entry_tokens > remaining_budget:
            dropped_reasons[key] = "budget_overflow"
            on_drop(key, "budget_overflow", {"entry_tokens": entry_tokens, "remaining_budget": remaining_budget})
            continue
        injected_texts.append(body)
        injected_entry_keys.append(key)
        remaining_budget -= entry_tokens
        on_success(entry, body, entry_tokens, truncated)

    return injected_texts, injected_entry_keys, dropped_reasons


@dataclass(slots=True)
class _GlobalCandidate:
    engine: LoreBookRuntimeEngine
    entry: LoreEntry
    order: int


class MultiLoreBookRuntimeEngine:
    """Run multiple lorebooks, then globally sort/inject one merged result."""

    def __init__(self, engines: list[LoreBookRuntimeEngine]):
        self._engines = engines

    def run(self, context: RuntimeContext) -> RuntimeResult:
        if not self._engines:
            return RuntimeResult("", [], [], {}, [])

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

            sorted_entries = engine.sort_expanded(
                pre_inject.expanded,
                context,
                pre_inject.events,
                pre_inject.match_scores,
            )
            candidates.extend(
                _GlobalCandidate(engine=engine, entry=entry, order=entry.resolved.injection.order)
                for entry in sorted_entries
            )

        candidates.sort(key=lambda c: (c.order, c.engine.lorebook.id, c.entry.id))
        total_budget = sum(engine.lorebook.budget.max_tokens for engine in self._engines)

        # Map entry object id → (qualified_key, engine) for O(1) callback lookup.
        entry_meta: dict[int, tuple[str, LoreBookRuntimeEngine]] = {
            id(c.entry): (f"{c.engine.lorebook.id}:{c.entry.id}", c.engine) for c in candidates
        }
        flat_entries = [c.entry for c in candidates]

        def _entry_key(entry: LoreEntry) -> str:
            return entry_meta[id(entry)][0]

        def on_success(entry: LoreEntry, body: str, entry_tokens: int, truncated: bool) -> None:
            key, engine = entry_meta[id(entry)]
            engine.apply_after_injection(entry, context)
            metrics: dict = {"entry_tokens": entry_tokens}
            if truncated:
                metrics["truncated"] = True
            engine.emit_event(events, context, entry.id, Stage.INJECT, "inserted", "inserted", metrics)

        def on_drop(key: str, reason: str, metrics: dict) -> None:
            # Resolve engine from key (lorebook_id:entry_id).
            lorebook_id, entry_id = key.split(":", 1)
            for engine in self._engines:
                if engine.lorebook.id == lorebook_id:
                    engine.emit_event(events, context, entry_id, Stage.INJECT, "dropped", reason, metrics)
                    break

        injected_texts, injected_entries, dropped_reasons = inject_budgeted(
            entries=flat_entries,
            context=context,
            events=events,
            dropped_reasons=dropped_reasons,
            remaining_budget=total_budget,
            entry_key=_entry_key,
            prepare_body=lambda entry, ctx: entry_meta[id(entry)][1].prepare_entry_body(entry, ctx),
            on_success=on_success,
            on_drop=on_drop,
        )

        return RuntimeResult(
            injected_prompt="\n\n".join(injected_texts),
            matched_entries=matched_entries,
            injected_entries=injected_entries,
            dropped_reasons=dropped_reasons,
            events=events,
        )
