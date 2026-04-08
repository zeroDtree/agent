import json
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

import prompt_manager.preset as preset_module
from prompt_manager.preset import build_preset_result, get_base_preset_messages


def _write_test_lorebook(
    root: Path,
    lorebook_id: str,
    keyword: str,
    content: str,
    order: int,
    position: str = "after_character",
) -> None:
    lorebook_dir = root / lorebook_id
    lorebook_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "id": lorebook_id,
        "name": lorebook_id,
        "enabled": True,
        "description": "",
        "merge_strategy": "global_sorted_merge",
        "source_scope": ["global"],
        "merge_policy": {"mode": "global_sorted_merge", "priority": ["global"]},
        "budget": {"max_tokens": 100, "overflow_policy": "drop_low_priority"},
        "defaults": {"position": position, "probability": 1.0, "case_sensitive": False},
        "runtime": {"max_recursion_steps": 3, "random_seed_strategy": "session_stable", "log_level": "normal"},
        "entries": [
            {
                "id": f"{lorebook_id}-entry",
                "path": f"entries/{lorebook_id}-entry.md",
                "enabled": True,
                "content": content,
                "resolved": {
                    "triggers": {"keywords": [keyword], "regex": [], "case_sensitive": False, "whole_word": False},
                    "filters": {"role_allowlist": [], "role_denylist": []},
                    "injection": {
                        "position": position,
                        "order": order,
                        "message_type": None,
                        "outlet": None,
                        "depth": None,
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
                    "budget": {"max_tokens": 100, "truncate": "tail"},
                },
            }
        ],
    }
    (lorebook_dir / "lorebook.json").write_text(json.dumps(payload), encoding="utf-8")


def test_build_preset_result_include_base_only_when_enabled() -> None:
    no_match_text = "zz_no_lorebook_keyword_match_zz"

    first_turn_messages = build_preset_result(
        user_input=no_match_text,
        thread_id="session-1",
        turn_index=1,
        include_base_messages=True,
    ).messages
    later_turn_messages = build_preset_result(
        user_input=no_match_text,
        thread_id="session-1",
        turn_index=2,
        include_base_messages=False,
    ).messages

    assert len(first_turn_messages) == len(get_base_preset_messages())
    assert later_turn_messages == []


def test_build_preset_result_injects_lorebook_per_turn() -> None:
    matched_text = "please use uv run python and pytest"

    messages = build_preset_result(
        user_input=matched_text,
        thread_id="session-2",
        turn_index=2,
        include_base_messages=False,
    ).messages

    assert len(messages) >= 1
    assert isinstance(messages[0], SystemMessage)
    assert str(messages[0].content).strip()


def test_build_preset_result_loads_multiple_lorebooks(monkeypatch, tmp_path: Path) -> None:
    lorebook_root = tmp_path / "lorebooks"
    _write_test_lorebook(lorebook_root, "lb-a", "trigger-a", "A content", order=20)
    _write_test_lorebook(lorebook_root, "lb-b", "trigger-b", "B content", order=5)

    monkeypatch.setattr(
        preset_module,
        "_DEFAULT_ENGINE_MANAGER",
        preset_module.LoreBookEngineManager(lorebook_root),
    )

    messages = build_preset_result(
        user_input="trigger-a and trigger-b",
        thread_id="multi-session",
        turn_index=1,
        lorebook_ids=["lb-a", "lb-b"],
        include_base_messages=False,
    ).messages

    assert len(messages) == 2
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], SystemMessage)
    assert str(messages[0].content) == "B content"
    assert str(messages[1].content) == "A content"


def test_build_preset_result_places_before_and_after_adjacent_to_character_defs(monkeypatch, tmp_path: Path) -> None:
    lorebook_root = tmp_path / "lorebooks"
    _write_test_lorebook(
        lorebook_root,
        "lb-before",
        "trigger-before",
        "Before character definitions",
        order=10,
        position="before_character",
    )
    _write_test_lorebook(
        lorebook_root,
        "lb-after",
        "trigger-after",
        "After character definitions",
        order=20,
        position="after_character",
    )

    monkeypatch.setattr(
        preset_module,
        "_DEFAULT_ENGINE_MANAGER",
        preset_module.LoreBookEngineManager(lorebook_root),
    )

    messages = build_preset_result(
        user_input="trigger-before trigger-after",
        thread_id="positioned-session",
        turn_index=1,
        lorebook_ids=["lb-before", "lb-after"],
        include_base_messages=True,
    ).messages

    assert len(messages) == 7
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], AIMessage)
    assert isinstance(messages[2], HumanMessage)
    assert isinstance(messages[3], AIMessage)
    assert isinstance(messages[4], SystemMessage)
    assert "Before character definitions" in str(messages[4].content)
    assert isinstance(messages[5], HumanMessage)
    assert isinstance(messages[6], SystemMessage)
    assert "After character definitions" in str(messages[6].content)


def test_build_preset_result_include_base_disabled_keeps_positional_entries_stable(monkeypatch, tmp_path: Path) -> None:
    lorebook_root = tmp_path / "lorebooks"
    _write_test_lorebook(
        lorebook_root,
        "lb-before",
        "trigger-before",
        "Before no base",
        order=5,
        position="before_character",
    )
    _write_test_lorebook(
        lorebook_root,
        "lb-after",
        "trigger-after",
        "After no base",
        order=10,
        position="after_character",
    )

    monkeypatch.setattr(
        preset_module,
        "_DEFAULT_ENGINE_MANAGER",
        preset_module.LoreBookEngineManager(lorebook_root),
    )

    messages = build_preset_result(
        user_input="trigger-before trigger-after",
        thread_id="positioned-no-base-session",
        turn_index=2,
        lorebook_ids=["lb-before", "lb-after"],
        include_base_messages=False,
    ).messages

    assert len(messages) == 2
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], SystemMessage)
    assert "Before no base" in str(messages[0].content)
    assert "After no base" in str(messages[1].content)


def test_build_preset_result_uses_custom_character_prompt_path(tmp_path: Path) -> None:
    custom_prompt = tmp_path / "custom_role.md"
    custom_prompt.write_text("<character-information>\ncustom-role\n</character-information>", encoding="utf-8")

    messages = build_preset_result(
        user_input="no-match-for-lorebook",
        thread_id="session-custom-role",
        turn_index=1,
        include_base_messages=True,
        character_prompt_path=str(custom_prompt),
    ).messages

    human_messages = [msg for msg in messages if isinstance(msg, HumanMessage)]
    assert len(human_messages) == 2
    combined = "\n".join(str(m.content) for m in human_messages)
    assert "custom-role" in combined


def test_preset_segment_order_character_before_core() -> None:
    messages = build_preset_result(
        user_input="zz_no_lorebook_keyword_match_zz",
        thread_id="reorder-session",
        turn_index=1,
        include_base_messages=True,
        preset_segment_order=["character", "core"],
        preset_segments_enabled={
            "core": True,
            "character": True,
            "persona": False,
        },
    ).messages

    assert isinstance(messages[0], HumanMessage)


def test_lorebook_before_core_and_after_character(monkeypatch, tmp_path: Path) -> None:
    lorebook_root = tmp_path / "lorebooks"
    _write_test_lorebook(
        lorebook_root,
        "lb-head",
        "hit-head",
        "Inject before core",
        order=5,
        position="before_core",
    )
    _write_test_lorebook(
        lorebook_root,
        "lb-mid",
        "hit-mid",
        "Inject after character",
        order=10,
        position="after_character",
    )

    monkeypatch.setattr(
        preset_module,
        "_DEFAULT_ENGINE_MANAGER",
        preset_module.LoreBookEngineManager(lorebook_root),
    )

    messages = build_preset_result(
        user_input="hit-head hit-mid",
        thread_id="anchor-session",
        turn_index=1,
        lorebook_ids=["lb-head", "lb-mid"],
        include_base_messages=True,
    ).messages

    assert isinstance(messages[0], SystemMessage)
    assert "Inject before core" in str(messages[0].content)
    assert isinstance(messages[1], SystemMessage)
    assert isinstance(messages[2], AIMessage)
    assert isinstance(messages[3], HumanMessage)
    assert isinstance(messages[4], AIMessage)
    assert isinstance(messages[5], HumanMessage)
    assert isinstance(messages[6], SystemMessage)
    assert "Inject after character" in str(messages[6].content)


def test_build_preset_result_raises_for_missing_character_prompt() -> None:
    try:
        build_preset_result(
            user_input="no-match-for-lorebook",
            thread_id="session-missing-role",
            turn_index=1,
            include_base_messages=True,
            character_prompt_path="prompts/chars/does-not-exist.md",
        )
    except FileNotFoundError as exc:
        assert "does-not-exist.md" in str(exc)
    else:
        raise AssertionError("Expected FileNotFoundError for missing character prompt file")
