from __future__ import annotations

from ..types import Lorebook, LoreEntry, RuntimeContext


class LorebookSessionState:
    """Per-engine sticky and cooldown maps keyed by (session_id, lorebook_id, entry_id)."""

    def __init__(self, lorebook: Lorebook):
        self._lorebook = lorebook
        self._sticky_state: dict[tuple[str, str, str], int] = {}
        self._cooldown_state: dict[tuple[str, str, str], int] = {}

    def is_sticky_active(self, entry: LoreEntry, context: RuntimeContext) -> bool:
        state_key = (context.session_id, self._lorebook.id, entry.id)
        sticky_until = self._sticky_state.get(state_key)
        return sticky_until is not None and sticky_until >= context.turn_index

    def is_cooldown_active(self, entry: LoreEntry, context: RuntimeContext) -> bool:
        advanced = entry.resolved.advanced
        if not advanced.cooldown_turns:
            return False
        state_key = (context.session_id, self._lorebook.id, entry.id)
        return self._cooldown_state.get(state_key, -1) >= context.turn_index

    def apply_after_injection(self, entry: LoreEntry, context: RuntimeContext) -> None:
        state_key = (context.session_id, self._lorebook.id, entry.id)
        advanced = entry.resolved.advanced
        if advanced.sticky_turns:
            self._sticky_state[state_key] = context.turn_index + advanced.sticky_turns
        if advanced.cooldown_turns:
            self._cooldown_state[state_key] = context.turn_index + advanced.cooldown_turns
