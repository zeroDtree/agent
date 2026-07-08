from __future__ import annotations

import re

from ..types import LoreBook, LoreEntry, RuntimeContext, RuntimeEvent, Stage
from .events import RuntimeEventSink
from .session_state import LoreBookSessionState


class LoreMatcher:
    """Match stage: keyword/regex triggers and sticky entries."""

    def __init__(self, lorebook: LoreBook, state: LoreBookSessionState, sink: RuntimeEventSink):
        self._lorebook = lorebook
        self._state = state
        self._sink = sink

    def combined_text(self, context: RuntimeContext) -> str:
        if not context.source_texts:
            return context.text
        selected_chunks: list[str] = [context.text]
        for source_name, source_text in context.source_texts.items():
            if source_name in context.active_sources and source_name in self._lorebook.source_scope:
                selected_chunks.append(source_text)
        return "\n\n".join(selected_chunks)

    def _score_and_reason(self, entry: LoreEntry, text: str, flags: int) -> tuple[int, str | None]:
        """Single pass over all triggers; returns (total_hit_count, first_match_reason).

        Returns (0, None) when no trigger fires.
        """
        triggers = entry.resolved.triggers
        score = 0
        first_reason: str | None = None

        for keyword in triggers.keywords:
            if triggers.whole_word:
                hits = len(re.compile(rf"\b{re.escape(keyword)}\b", flags=flags).findall(text))
            elif triggers.case_sensitive:
                hits = text.count(keyword)
            else:
                hits = text.lower().count(keyword.lower())
            if hits:
                score += hits
                first_reason = first_reason or "keyword_hit"

        for regex_pattern in triggers.regex:
            hits = len(re.findall(regex_pattern, text, flags=flags))
            if hits:
                score += hits
                first_reason = first_reason or "regex_hit"

        return score, first_reason

    def _match_result_for_text(
        self, entry: LoreEntry, text: str, events: list[RuntimeEvent], context: RuntimeContext
    ) -> tuple[int, bool]:
        """Return (score, matched) given precomputed text; emit the matched event on a hit."""
        triggers = entry.resolved.triggers
        flags = 0 if triggers.case_sensitive else re.IGNORECASE
        score, reason = self._score_and_reason(entry, text, flags)
        if reason is not None:
            self._sink.event(events, context, entry.id, Stage.MATCH, "matched", reason)
            return score, True
        return 0, False

    def match_hit_score(
        self, entry: LoreEntry, context: RuntimeContext, events: list[RuntimeEvent]
    ) -> tuple[int, bool]:
        """Public API: return (score, matched) and emit the matched event on a hit."""
        text = self.combined_text(context)
        return self._match_result_for_text(entry, text, events, context)

    def run_match(
        self,
        active_entries: list[LoreEntry],
        context: RuntimeContext,
        events: list[RuntimeEvent],
    ) -> tuple[list[LoreEntry], dict[str, int]]:
        # Compute combined text once for all entries in this run.
        text = self.combined_text(context)
        matched: list[LoreEntry] = []
        match_scores: dict[str, int] = {}
        for entry in active_entries:
            if self._state.is_sticky_active(entry, context):
                matched.append(entry)
                self._sink.event(events, context, entry.id, Stage.MATCH, "matched", "sticky_active")
                triggers = entry.resolved.triggers
                flags = 0 if triggers.case_sensitive else re.IGNORECASE
                score, _ = self._score_and_reason(entry, text, flags)
                match_scores[entry.id] = score
                continue
            score, hit = self._match_result_for_text(entry, text, events, context)
            if hit:
                matched.append(entry)
                match_scores[entry.id] = score
        return matched, match_scores
