from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..types.conversation import MessageType
from ..types.lorebook import (
    EntryAdvanced,
    EntryBudget,
    EntryFilters,
    EntryInjection,
    EntryResolved,
    EntryTriggers,
    InjectionPositionType,
)
from .front_matter import parse_markdown_entry
from .schema import validate_lorebook_json

_DEFAULT_INJECTION_POSITION = InjectionPositionType.AFTER_CHARACTER


def _entry_id_from_path(path: Path) -> str:
    return path.stem


def _make_entry_resolved(metadata: dict[str, Any]) -> EntryResolved:
    """Build a fully-resolved EntryResolved from raw front matter, applying defaults."""
    triggers = metadata.get("triggers", {})
    injection = metadata.get("injection", {})
    advanced = metadata.get("advanced", {})
    budget = metadata.get("budget", {})

    raw_position = injection.get("position_type") or injection.get("position", _DEFAULT_INJECTION_POSITION)
    position_type = InjectionPositionType(str(raw_position))

    raw_message_type = injection.get("message_type")
    message_type = MessageType(raw_message_type) if raw_message_type is not None else None

    raw_depth = injection.get("depth")
    depth = int(raw_depth) if isinstance(raw_depth, (int, float)) and not isinstance(raw_depth, bool) else None

    return EntryResolved(
        triggers=EntryTriggers(
            keywords=triggers.get("keywords", []),
            regex=triggers.get("regex", []),
            case_sensitive=bool(triggers.get("case_sensitive", False)),
            whole_word=bool(triggers.get("whole_word", False)),
        ),
        filters=EntryFilters(),
        injection=EntryInjection(
            position_type=position_type,
            order=int(injection.get("order", 0)),
            message_type=message_type,
            depth=depth,
        ),
        advanced=EntryAdvanced(
            inclusion_group=advanced.get("inclusion_group"),
            group_scoring=bool(advanced.get("group_scoring", False)),
            probability=float(advanced.get("probability", 1.0)),
            recursive=bool(advanced.get("recursive", False)),
            max_recursion_depth=int(advanced.get("max_recursion_depth", 0)),
            sticky_turns=int(advanced.get("sticky_turns", 0)),
            cooldown_turns=int(advanced.get("cooldown_turns", 0)),
            delay_turns=int(advanced.get("delay_turns", 0)),
        ),
        budget=EntryBudget(
            max_tokens=int(budget.get("max_tokens", 300)),
            truncate=budget.get("truncate", "tail"),
        ),
    )


def build_lorebook(source: Path, output: Path) -> dict[str, Any]:
    """Build lorebook.json from entries/*.md source files."""
    entries_dir = source / "entries"
    if not entries_dir.exists():
        raise FileNotFoundError(f"Missing entries directory: {entries_dir}")

    entry_files = sorted(entries_dir.glob("*.md"))
    if not entry_files:
        raise ValueError(f"No Markdown entries found under: {entries_dir}")

    entries: list[dict[str, Any]] = []

    for entry_path in entry_files:
        metadata, content = parse_markdown_entry(entry_path)
        entry_id = str(metadata.get("id", _entry_id_from_path(entry_path)))
        resolved = asdict(_make_entry_resolved(metadata))

        entries.append(
            {
                "id": entry_id,
                "path": f"entries/{entry_path.name}",
                "enabled": bool(metadata.get("enabled", True)),
                "content": content,
                "resolved": resolved,
            }
        )

    lorebook: dict[str, Any] = {
        "id": source.name,
        "name": source.name.replace("-", " ").title(),
        "enabled": True,
        "description": f"LoreBook generated from {source}",
        "source_scope": ["global", "character", "persona", "chat"],
        "merge_policy": {
            "mode": "global_sorted_merge",
            "priority": ["character", "persona", "chat", "global"],
        },
        "budget": {
            "max_tokens": 2000,
            "overflow_policy": "drop_low_priority",
        },
        "runtime": {
            "max_recursion_steps": 3,
            "random_seed_strategy": "session_stable",
            "log_level": "normal",
        },
        "entries": entries,
    }

    validate_lorebook_json(lorebook)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(lorebook, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return lorebook
