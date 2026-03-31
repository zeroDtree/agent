import json
from pathlib import Path

import pytest
from jsonschema.exceptions import ValidationError

from prompt_manager.builder import build_lorebook
from prompt_manager.front_matter import parse_markdown_entry
from prompt_manager.loader import load_lorebook
from prompt_manager.schema import validate_lorebook_json


def test_parse_markdown_entry_without_front_matter(tmp_path: Path) -> None:
    entry = tmp_path / "e.md"
    entry.write_text("plain body", encoding="utf-8")
    metadata, body = parse_markdown_entry(entry)
    assert metadata == {}
    assert body == "plain body"


def test_parse_markdown_entry_invalid_front_matter_shape(tmp_path: Path) -> None:
    entry = tmp_path / "e.md"
    entry.write_text("---\n- not-a-map\n---\nbody", encoding="utf-8")
    metadata, body = parse_markdown_entry(entry)
    assert metadata == {}
    assert body == "body"


def test_build_lorebook_missing_entries_dir_raises(tmp_path: Path) -> None:
    source = tmp_path / "book"
    source.mkdir(parents=True)
    with pytest.raises(FileNotFoundError):
        build_lorebook(source=source, output=tmp_path / "out.json")


def test_build_lorebook_empty_entries_raises(tmp_path: Path) -> None:
    source = tmp_path / "book"
    (source / "entries").mkdir(parents=True)
    with pytest.raises(ValueError):
        build_lorebook(source=source, output=tmp_path / "out.json")


def test_build_output_loads_and_passes_schema(tmp_path: Path) -> None:
    source = tmp_path / "book"
    entries_dir = source / "entries"
    entries_dir.mkdir(parents=True)
    (entries_dir / "a.md").write_text(
        '---\ntriggers:\n  keywords: ["ship"]\nadvanced:\n  probability: 0.5\n---\nentry body',
        encoding="utf-8",
    )
    out = tmp_path / "lorebook.json"
    built = build_lorebook(source=source, output=out)

    validate_lorebook_json(built)
    lorebook = load_lorebook(out)
    assert lorebook.id == "book"
    assert lorebook.entries[0].id == "a"
    assert lorebook.entries[0].resolved.advanced.probability == 0.5


def test_schema_rejects_invalid_payload(tmp_path: Path) -> None:
    bad = {"id": "x", "entries": []}
    with pytest.raises(ValidationError):
        validate_lorebook_json(bad)


def test_loader_parses_numeric_depth_to_int(tmp_path: Path) -> None:
    data = {
        "id": "depth-book",
        "name": "Depth",
        "enabled": True,
        "description": "",
        "merge_strategy": "global_sorted_merge",
        "source_scope": ["global"],
        "merge_policy": {"mode": "global_sorted_merge", "priority": ["global"]},
        "budget": {"max_tokens": 50, "overflow_policy": "drop_low_priority"},
        "defaults": {"position": "after_char_defs", "probability": 1.0, "case_sensitive": False},
        "runtime": {"max_recursion_steps": 1, "random_seed_strategy": "session_stable", "log_level": "normal"},
        "entries": [
            {
                "id": "d",
                "path": "entries/d.md",
                "enabled": True,
                "content": "x",
                "resolved": {
                    "triggers": {"keywords": ["x"], "regex": [], "case_sensitive": False, "whole_word": False},
                    "filters": {"role_allowlist": [], "role_denylist": []},
                    "injection": {
                        "position": "depth",
                        "order": 0,
                        "message_type": None,
                        "outlet": None,
                        "depth": 2.0,
                    },
                    "advanced": {
                        "inclusion_group": None,
                        "group_scoring": False,
                        "probability": 1.0,
                        "recursive": False,
                        "max_recursion_depth": 0,
                        "sticky_turns": 0,
                        "cooldown_turns": 0,
                        "delay_turns": 0,
                    },
                    "budget": {"max_tokens": 20, "truncate": "tail"},
                },
            }
        ],
    }
    path = tmp_path / "book.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    loaded = load_lorebook(path)
    assert loaded.entries[0].resolved.injection.depth == 2
