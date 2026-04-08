from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .front_matter import parse_markdown_entry


def _entry_id_from_path(path: Path) -> str:
    return path.stem


def _default_runtime_resolved(metadata: dict[str, Any], book_defaults: dict[str, Any]) -> dict[str, Any]:
    triggers = metadata.get("triggers", {})
    filters = metadata.get("filters", {})
    injection = metadata.get("injection", {})
    advanced = metadata.get("advanced", {})
    budget = metadata.get("budget", {})
    position = str(injection.get("position", book_defaults["position"]))
    message_type_raw = injection.get("message_type", None)
    if message_type_raw is None:
        message_type = None
    else:
        message_type = str(message_type_raw)
    depth_raw = injection.get("depth", None)
    if depth_raw is None:
        depth = None
    elif isinstance(depth_raw, (int, float)) and not isinstance(depth_raw, bool):
        depth = int(depth_raw)
    else:
        depth = None
    return {
        "triggers": {
            "keywords": triggers.get("keywords", []),
            "regex": triggers.get("regex", []),
            "case_sensitive": bool(triggers.get("case_sensitive", book_defaults["case_sensitive"])),
            "whole_word": bool(triggers.get("whole_word", False)),
        },
        "filters": {
            "role_allowlist": filters.get("role_allowlist", []),
            "role_denylist": filters.get("role_denylist", []),
        },
        "injection": {
            "position": position,
            "order": int(injection.get("order", 0)),
            "message_type": message_type,
            "outlet": injection.get("outlet", None),
            "depth": depth,
        },
        "advanced": {
            "inclusion_group": advanced.get("inclusion_group", None),
            "group_scoring": bool(advanced.get("group_scoring", False)),
            "probability": float(advanced.get("probability", book_defaults["probability"])),
            "recursive": bool(advanced.get("recursive", False)),
            "max_recursion_depth": int(advanced.get("max_recursion_depth", 0)),
            "sticky_turns": int(advanced.get("sticky_turns", 0)),
            "cooldown_turns": int(advanced.get("cooldown_turns", 0)),
            "delay_turns": int(advanced.get("delay_turns", 0)),
        },
        "budget": {
            "max_tokens": int(budget.get("max_tokens", 300)),
            "truncate": budget.get("truncate", "tail"),
        },
    }


def build_lorebook(source: Path, output: Path) -> dict[str, Any]:
    """Build lorebook.json from entries/*.md source files."""
    entries_dir = source / "entries"
    if not entries_dir.exists():
        raise FileNotFoundError(f"Missing entries directory: {entries_dir}")

    entry_files = sorted(entries_dir.glob("*.md"))
    if not entry_files:
        raise ValueError(f"No Markdown entries found under: {entries_dir}")

    book_defaults = {
        "position": "after_character",
        "probability": 1.0,
        "case_sensitive": False,
    }

    entries: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for entry_path in entry_files:
        metadata, content = parse_markdown_entry(entry_path)
        entry_id = str(metadata.get("id", _entry_id_from_path(entry_path)))
        seen_ids.add(entry_id)
        resolved = _default_runtime_resolved(metadata, book_defaults)

        entries.append(
            {
                "id": entry_id,
                "path": f"entries/{entry_path.name}",
                "enabled": bool(metadata.get("enabled", True)),
                "content": content,
                "resolved": resolved,
            }
        )

    lorebook_max_tokens = 2000

    lorebook = {
        "id": source.name,
        "name": source.name.replace("-", " ").title(),
        "enabled": True,
        "description": f"LoreBook generated from {source}",
        "source_scope": ["global", "character", "persona", "chat"],
        "merge_strategy": "global_sorted_merge",
        "merge_policy": {
            "mode": "global_sorted_merge",
            "priority": ["character", "persona", "chat", "global"],
        },
        "budget": {
            "max_tokens": lorebook_max_tokens,
            "overflow_policy": "drop_low_priority",
        },
        "defaults": book_defaults,
        "runtime": {
            "max_recursion_steps": 3,
            "random_seed_strategy": "session_stable",
            "log_level": "normal",
            "injection_order": "small_first",
        },
        "entries": entries,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(lorebook, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return lorebook
