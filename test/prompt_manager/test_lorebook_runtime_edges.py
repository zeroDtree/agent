import json
from pathlib import Path

from prompt_manager.loader import load_lorebook
from prompt_manager.runtime import LorebookRuntimeEngine
from prompt_manager.types import RuntimeContext


def _base_lorebook_dict() -> dict:
    return {
        "id": "edge-lb",
        "name": "Edge",
        "enabled": True,
        "description": "",
        "merge_strategy": "global_sorted_merge",
        "source_scope": ["global", "character"],
        "merge_policy": {"mode": "global_sorted_merge", "priority": ["global"]},
        "budget": {"max_tokens": 100, "overflow_policy": "drop_low_priority"},
        "defaults": {
            "position": "after_char_defs",
            "probability": 1.0,
            "case_sensitive": False,
        },
        "runtime": {
            "max_recursion_steps": 3,
            "random_seed_strategy": "session_stable",
            "log_level": "normal",
            "injection_order": "small_first",
        },
        "entries": [],
    }


def _entry(
    eid: str,
    content: str,
    keywords: list[str],
    *,
    regex: list[str] | None = None,
    whole_word: bool = False,
    order: int = 100,
    sticky_turns: int = 0,
    cooldown_turns: int = 0,
    delay_turns: int = 0,
    truncate: str = "tail",
    max_tokens: int = 100,
    outlet: str | None = None,
) -> dict:
    return {
        "id": eid,
        "path": f"entries/{eid}.md",
        "enabled": True,
        "content": content,
        "resolved": {
            "triggers": {
                "keywords": keywords,
                "regex": regex or [],
                "case_sensitive": False,
                "whole_word": whole_word,
            },
            "filters": {"role_allowlist": [], "role_denylist": []},
            "injection": {
                "position": "after_char_defs",
                "order": order,
                "message_type": None,
                "outlet": outlet,
                "depth": None,
            },
            "advanced": {
                "inclusion_group": None,
                "group_scoring": False,
                "probability": 1.0,
                "recursive": False,
                "max_recursion_depth": 0,
                "sticky_turns": sticky_turns,
                "cooldown_turns": cooldown_turns,
                "delay_turns": delay_turns,
            },
            "budget": {"max_tokens": max_tokens, "truncate": truncate},
        },
    }


def _load_engine(data: dict, tmp_path: Path) -> LorebookRuntimeEngine:
    path = tmp_path / "edge-book.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    lorebook = load_lorebook(path)
    return LorebookRuntimeEngine(lorebook)


def test_source_scope_uses_active_source_texts(tmp_path: Path) -> None:
    data = _base_lorebook_dict()
    data["entries"] = [_entry("from-character", "c", ["char_hit"])]
    engine = _load_engine(data, tmp_path)
    result = engine.run(
        RuntimeContext(
            request_id="r1",
            session_id="s1",
            role="assistant",
            text="no-hit",
            source_texts={"character": "char_hit"},
            active_sources={"character"},
            tags=set(),
            turn_index=1,
        )
    )
    assert result.injected_entries == ["from-character"]


def test_whole_word_prevents_substring_match(tmp_path: Path) -> None:
    data = _base_lorebook_dict()
    data["entries"] = [_entry("exact", "body", ["cat"], whole_word=True)]
    engine = _load_engine(data, tmp_path)
    result = engine.run(
        RuntimeContext(
            request_id="r1",
            session_id="s1",
            role="assistant",
            text="concatenate",
            tags=set(),
            turn_index=1,
        )
    )
    assert "exact" not in result.matched_entries


def test_regex_trigger_matches(tmp_path: Path) -> None:
    data = _base_lorebook_dict()
    data["entries"] = [_entry("rx", "body", [], regex=[r"\d{4}-\d{2}-\d{2}"])]
    engine = _load_engine(data, tmp_path)
    result = engine.run(
        RuntimeContext(
            request_id="r1",
            session_id="s1",
            role="assistant",
            text="ship at 2026-03-31",
            tags=set(),
            turn_index=1,
        )
    )
    assert "rx" in result.injected_entries


def test_delay_and_cooldown_apply_across_turns(tmp_path: Path) -> None:
    data = _base_lorebook_dict()
    data["entries"] = [_entry("gated", "body", ["fire"], delay_turns=2, cooldown_turns=2)]
    engine = _load_engine(data, tmp_path)

    turn1 = engine.run(
        RuntimeContext("r1", "s1", "assistant", "fire", tags=set(), turn_index=1),
    )
    assert turn1.dropped_reasons["gated"] == "delay_not_reached"

    turn2 = engine.run(
        RuntimeContext("r2", "s1", "assistant", "fire", tags=set(), turn_index=2),
    )
    assert "gated" in turn2.injected_entries

    turn3 = engine.run(
        RuntimeContext("r3", "s1", "assistant", "fire", tags=set(), turn_index=3),
    )
    assert turn3.dropped_reasons["gated"] == "cooldown_active"


def test_sticky_turns_match_without_trigger_on_next_turn(tmp_path: Path) -> None:
    data = _base_lorebook_dict()
    data["entries"] = [_entry("sticky", "body", ["fire"], sticky_turns=1)]
    engine = _load_engine(data, tmp_path)

    first = engine.run(RuntimeContext("r1", "s1", "assistant", "fire", tags=set(), turn_index=1))
    assert "sticky" in first.injected_entries

    second = engine.run(RuntimeContext("r2", "s1", "assistant", "miss", tags=set(), turn_index=2))
    assert "sticky" in second.matched_entries
    assert any(e.reason == "sticky_active" for e in second.events)


def test_outlet_not_referenced_drops_entry(tmp_path: Path) -> None:
    data = _base_lorebook_dict()
    data["entries"] = [_entry("out", "body", ["go"], outlet="facts")]
    engine = _load_engine(data, tmp_path)
    result = engine.run(RuntimeContext("r1", "s1", "assistant", "go", tags=set(), turn_index=1))
    assert result.dropped_reasons["out"] == "outlet_not_referenced"


def test_truncate_head_policy_keeps_last_words(tmp_path: Path) -> None:
    data = _base_lorebook_dict()
    data["budget"] = {"max_tokens": 4, "overflow_policy": "truncate_head"}
    data["entries"] = [
        _entry("e1", "one two three", ["go"], max_tokens=100),
        _entry("e2", "four five six", ["go"], max_tokens=100),
    ]
    engine = _load_engine(data, tmp_path)
    result = engine.run(RuntimeContext("r1", "s1", "assistant", "go", tags=set(), turn_index=1))
    assert result.injected_prompt == "one two three four"
