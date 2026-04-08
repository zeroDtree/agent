from __future__ import annotations

import random

from ..types import LoreBook, LoreEntry, RuntimeContext, RuntimeEvent
from .events import RuntimeEventSink
from .helpers import stable_int_seed
from .session_state import LoreBookSessionState


class LoreFilterStage:
    """Filter stage: delay, cooldown, role, probability."""

    def __init__(self, lorebook: LoreBook, state: LoreBookSessionState, sink: RuntimeEventSink):
        self._lorebook = lorebook
        self._state = state
        self._sink = sink

    def _probability_seed(self, entry: LoreEntry, context: RuntimeContext) -> int:
        if context.seed is not None:
            return context.seed
        strategy = self._lorebook.runtime.random_seed_strategy
        if strategy == "session_stable":
            return stable_int_seed("lorebook.probability", self._lorebook.id, context.session_id, entry.id)
        return stable_int_seed(
            "lorebook.probability", self._lorebook.id, context.session_id, context.request_id, entry.id
        )

    def filter_reason(self, entry: LoreEntry, context: RuntimeContext) -> str | None:
        advanced = entry.resolved.advanced
        if advanced.delay_turns and context.turn_index < advanced.delay_turns:
            return "delay_not_reached"
        if advanced.cooldown_turns and self._state.is_cooldown_active(entry, context):
            return "cooldown_active"
        if entry.resolved.filters.role_allowlist and context.role not in entry.resolved.filters.role_allowlist:
            return "role_denied"
        if context.role in entry.resolved.filters.role_denylist:
            return "role_denied"
        if advanced.probability < 1.0:
            seed = self._probability_seed(entry, context)
            random_value = random.Random(seed).random()
            if random_value > advanced.probability:
                return "probability_drop"
        return None

    def run_filter(
        self,
        matched: list[LoreEntry],
        context: RuntimeContext,
        events: list[RuntimeEvent],
    ) -> tuple[list[LoreEntry], dict[str, str]]:
        filtered: list[LoreEntry] = []
        dropped_reasons: dict[str, str] = {}
        for entry in matched:
            reason = self.filter_reason(entry, context)
            if reason is None:
                filtered.append(entry)
                self._sink.event(events, context, entry.id, "filter", "passed", "filters_passed")
            else:
                dropped_reasons[entry.id] = reason
                self._sink.event(events, context, entry.id, "filter", "dropped", reason)
        return filtered, dropped_reasons
