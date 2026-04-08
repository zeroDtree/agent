from __future__ import annotations

from ..types import LoreBook, LoreEntry, RuntimeContext, RuntimeEvent
from .events import RuntimeEventSink
from .helpers import clip_text_to_token_budget, token_count
from .session_state import LoreBookSessionState


class LoreInjector:
    """Inject stage: per-entry body prep, outlets, book budget, sticky/cooldown updates."""

    def __init__(self, lorebook: LoreBook, state: LoreBookSessionState, sink: RuntimeEventSink):
        self._lorebook = lorebook
        self._state = state
        self._sink = sink

    def prepare_entry_body(self, entry: LoreEntry, context: RuntimeContext) -> tuple[str | None, int, bool]:
        """Return (body, token_count, truncated) or (None, raw_token_count, False) if dropped."""
        raw = entry.content
        raw_tokens = token_count(raw)
        max_tok = entry.resolved.budget.max_tokens
        truncate_mode = entry.resolved.budget.truncate

        if raw_tokens <= max_tok:
            return raw, raw_tokens, False

        if truncate_mode == "none":
            return None, raw_tokens, False

        clipped = clip_text_to_token_budget(raw, max_tok, truncate_mode)
        return clipped, token_count(clipped), True

    def inject_drop_low_priority(
        self,
        sorted_entries: list[LoreEntry],
        context: RuntimeContext,
        events: list[RuntimeEvent],
        dropped_reasons: dict[str, str],
    ) -> tuple[str, list[str], dict[str, str]]:
        injected_texts: list[str] = []
        injected_entries: list[str] = []
        remaining_budget = self._lorebook.budget.max_tokens

        for entry in sorted_entries:
            body, entry_tokens, truncated = self.prepare_entry_body(entry, context)
            if body is None:
                dropped_reasons[entry.id] = "entry_budget_overflow"
                self._sink.event(
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
                dropped_reasons[entry.id] = "budget_overflow"
                self._sink.event(
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
                dropped_reasons[entry.id] = "outlet_not_referenced"
                self._sink.event(events, context, entry.id, "inject", "dropped", "outlet_not_referenced")
                continue
            injected_texts.append(body)
            injected_entries.append(entry.id)
            remaining_budget -= entry_tokens
            self._state.apply_after_injection(entry, context)
            metrics: dict = {"entry_tokens": entry_tokens}
            if truncated:
                metrics["truncated"] = True
            self._sink.event(events, context, entry.id, "inject", "inserted", "inserted", metrics)

        return "\n\n".join(injected_texts), injected_entries, dropped_reasons

    def inject_merge_truncate(
        self,
        sorted_entries: list[LoreEntry],
        context: RuntimeContext,
        events: list[RuntimeEvent],
        dropped_reasons: dict[str, str],
        overflow_policy: str,
    ) -> tuple[str, list[str], dict[str, str]]:
        injected_texts: list[str] = []
        injected_entries: list[str] = []

        for entry in sorted_entries:
            body, entry_tokens, truncated = self.prepare_entry_body(entry, context)
            if body is None:
                dropped_reasons[entry.id] = "entry_budget_overflow"
                self._sink.event(
                    events,
                    context,
                    entry.id,
                    "inject",
                    "dropped",
                    "entry_budget_overflow",
                    {"entry_tokens": entry_tokens, "entry_budget": entry.resolved.budget.max_tokens},
                )
                continue
            if entry.resolved.injection.outlet and entry.resolved.injection.outlet not in context.outlet_references:
                dropped_reasons[entry.id] = "outlet_not_referenced"
                self._sink.event(events, context, entry.id, "inject", "dropped", "outlet_not_referenced")
                continue
            injected_texts.append(body)
            injected_entries.append(entry.id)
            self._state.apply_after_injection(entry, context)
            metrics: dict = {"entry_tokens": entry_tokens}
            if truncated:
                metrics["truncated"] = True
            self._sink.event(events, context, entry.id, "inject", "inserted", "inserted", metrics)

        merged = "\n\n".join(injected_texts)
        book_max = self._lorebook.budget.max_tokens
        total_tokens = token_count(merged)
        if total_tokens > book_max:
            clip_mode = "tail" if overflow_policy == "truncate_tail" else "head"
            merged = clip_text_to_token_budget(merged, book_max, clip_mode)
            self._sink.event(
                events,
                context,
                None,
                "inject",
                "truncated",
                "merged_lorebook_truncated",
                {"total_tokens_before": total_tokens, "book_max_tokens": book_max, "clip_mode": clip_mode},
            )

        return merged, injected_entries, dropped_reasons
