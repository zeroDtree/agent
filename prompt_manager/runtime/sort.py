from __future__ import annotations

from collections import defaultdict

from ..types import LoreEntry, RuntimeContext, RuntimeEvent, Stage
from .events import RuntimeEventSink


class LoreSorter:
    """Sort stage: inclusion groups and injection order (ascending by injection.order)."""

    def __init__(self, sink: RuntimeEventSink):
        self._sink = sink

    def _sort_entries(
        self,
        entries: list[LoreEntry],
        context: RuntimeContext,
        events: list[RuntimeEvent],
        match_scores: dict[str, int],
    ) -> list[LoreEntry]:
        grouped: dict[str, list[LoreEntry]] = defaultdict(list)
        non_grouped: list[LoreEntry] = []
        for entry in entries:
            group = entry.resolved.advanced.inclusion_group
            if group:
                grouped[group].append(entry)
            else:
                non_grouped.append(entry)

        selected: list[LoreEntry] = []

        def _order_tiebreak(order: int) -> int:
            """Lower injection.order wins ties (ascending sort semantics)."""
            return -order

        for group_name, members in grouped.items():
            use_scoring = any(m.resolved.advanced.group_scoring for m in members)
            if use_scoring:
                winner = max(
                    members,
                    key=lambda item: (
                        match_scores.get(item.id, 0),
                        _order_tiebreak(item.resolved.injection.order),
                        item.id,
                    ),
                )
            else:
                winner = max(members, key=lambda item: (_order_tiebreak(item.resolved.injection.order), item.id))
            selected.append(winner)
            for loser in members:
                if loser.id != winner.id:
                    self._sink.event(
                        events,
                        context,
                        loser.id,
                        Stage.SORT,
                        "dropped",
                        "inclusion_group_conflict",
                        {"group": group_name},
                    )

        selected.extend(non_grouped)
        selected.sort(key=lambda item: item.resolved.injection.order)
        return selected

    def run_sort(
        self,
        expanded: list[LoreEntry],
        context: RuntimeContext,
        events: list[RuntimeEvent],
        match_scores: dict[str, int],
    ) -> list[LoreEntry]:
        return self._sort_entries(expanded, context, events, match_scores)
