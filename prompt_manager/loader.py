from __future__ import annotations

import json
from pathlib import Path

from .types import (
    EntryAdvanced,
    EntryBudget,
    EntryFilters,
    EntryInjection,
    EntryResolved,
    EntryTriggers,
    LoreBook,
    LoreBookBudget,
    LoreBookDefaults,
    LoreEntry,
    MergePolicy,
    RuntimeConfig,
)


def load_lorebook(path: str | Path) -> LoreBook:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    entries: list[LoreEntry] = []
    for raw_entry in data.get("entries", []):
        resolved = raw_entry["resolved"]
        entries.append(
            LoreEntry(
                id=raw_entry["id"],
                path=raw_entry["path"],
                enabled=raw_entry["enabled"],
                content=raw_entry["content"],
                resolved=EntryResolved(
                    triggers=EntryTriggers(**resolved["triggers"]),
                    filters=EntryFilters(**resolved["filters"]),
                    injection=EntryInjection(**resolved["injection"]),
                    advanced=EntryAdvanced(**resolved["advanced"]),
                    budget=EntryBudget(**resolved["budget"]),
                ),
            )
        )

    return LoreBook(
        id=data["id"],
        name=data["name"],
        enabled=data["enabled"],
        description=data.get("description", ""),
        merge_strategy=data["merge_strategy"],
        source_scope=data.get("source_scope", ["global"]),
        merge_policy=MergePolicy(**data.get("merge_policy", {})),
        budget=LoreBookBudget(**data["budget"]),
        defaults=LoreBookDefaults(**data["defaults"]),
        runtime=RuntimeConfig(**data.get("runtime", {})),
        entries=entries,
    )
