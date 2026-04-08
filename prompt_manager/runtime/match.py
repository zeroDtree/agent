from __future__ import annotations

import re

from ..types import LoreBook, LoreEntry, RuntimeContext, RuntimeEvent
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

    def is_matched(self, entry: LoreEntry, context: RuntimeContext, events: list[RuntimeEvent]) -> bool:
        text = self.combined_text(context)
        triggers = entry.resolved.triggers
        flags = 0 if triggers.case_sensitive else re.IGNORECASE

        for keyword in triggers.keywords:
            if triggers.whole_word:
                pattern = re.compile(rf"\b{re.escape(keyword)}\b", flags=flags)
                if pattern.search(text):
                    self._sink.event(events, context, entry.id, "match", "matched", "keyword_hit")
                    return True
            elif (keyword in text) if triggers.case_sensitive else (keyword.lower() in text.lower()):
                self._sink.event(events, context, entry.id, "match", "matched", "keyword_hit")
                return True

        for regex_pattern in triggers.regex:
            if re.search(regex_pattern, text, flags=flags):
                self._sink.event(events, context, entry.id, "match", "matched", "regex_hit")
                return True
        return False

    def match_score(self, entry: LoreEntry, context: RuntimeContext) -> int:
        """Match strength: keyword hit counts + regex match counts (aligned with match semantics)."""
        text = self.combined_text(context)
        triggers = entry.resolved.triggers
        flags = 0 if triggers.case_sensitive else re.IGNORECASE
        score = 0

        for keyword in triggers.keywords:
            if triggers.whole_word:
                pattern = re.compile(rf"\b{re.escape(keyword)}\b", flags=flags)
                score += len(pattern.findall(text))
            elif triggers.case_sensitive:
                score += text.count(keyword)
            else:
                score += text.lower().count(keyword.lower())

        for regex_pattern in triggers.regex:
            score += len(re.findall(regex_pattern, text, flags=flags))

        return score

    def run_match(
        self,
        active_entries: list[LoreEntry],
        context: RuntimeContext,
        events: list[RuntimeEvent],
    ) -> tuple[list[LoreEntry], dict[str, int]]:
        matched: list[LoreEntry] = []
        for entry in active_entries:
            if self._state.is_sticky_active(entry, context):
                matched.append(entry)
                self._sink.event(events, context, entry.id, "match", "matched", "sticky_active")
                continue
            if self.is_matched(entry, context, events):
                matched.append(entry)

        match_scores = {entry.id: self.match_score(entry, context) for entry in matched}
        return matched, match_scores
