from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path

from ..types import (
    EntryAdvanced,
    EntryBudget,
    EntryFilters,
    EntryInjection,
    EntryResolved,
    EntryTriggers,
    LoreBook,
    LoreBookBudget,
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
                    filters=EntryFilters(),
                    injection=EntryInjection(**resolved["injection"]),
                    advanced=EntryAdvanced(**resolved["advanced"]),
                    budget=EntryBudget(**resolved["budget"]),
                ),
            )
        )

    runtime_raw = data.get("runtime", {})
    runtime_keys = {f.name for f in fields(RuntimeConfig)}
    runtime_data = {k: v for k, v in runtime_raw.items() if k in runtime_keys}

    return LoreBook(
        id=data["id"],
        name=data["name"],
        enabled=data["enabled"],
        description=data.get("description", ""),
        source_scope=data.get("source_scope", ["global"]),
        merge_policy=MergePolicy(**data.get("merge_policy", {})),
        budget=LoreBookBudget(**data["budget"]),
        runtime=RuntimeConfig(**runtime_data),
        entries=entries,
    )
