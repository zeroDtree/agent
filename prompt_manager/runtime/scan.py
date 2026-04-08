from __future__ import annotations

from ..types import LoreBook, LoreEntry


class ActiveEntryScanner:
    """Scan stage: collect enabled entries from the lorebook."""

    def __init__(self, lorebook: LoreBook):
        self._lorebook = lorebook

    def collect_enabled_entries(self) -> list[LoreEntry]:
        return [entry for entry in self._lorebook.entries if entry.enabled]
