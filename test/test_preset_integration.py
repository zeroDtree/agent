import json
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

import utils.preset as preset_module
from utils.preset import BASE_PRESET_MESSAGES, build_preset_messages


def _write_test_lorebook(root: Path, lorebook_id: str, keyword: str, content: str, order: int) -> None:
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
        "defaults": {"position": "after_char_defs", "probability": 1.0, "case_sensitive": False},
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
                        "position": "after_char_defs",
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


def test_build_preset_messages_include_base_only_when_enabled() -> None:
    no_match_text = "zz_no_lorebook_keyword_match_zz"

    first_turn_messages = build_preset_messages(
        user_input=no_match_text,
        thread_id="session-1",
        turn_index=1,
        include_base_messages=True,
    )
    later_turn_messages = build_preset_messages(
        user_input=no_match_text,
        thread_id="session-1",
        turn_index=2,
        include_base_messages=False,
    )

    assert len(first_turn_messages) == len(BASE_PRESET_MESSAGES)
    assert later_turn_messages == []


def test_build_preset_messages_injects_lorebook_per_turn() -> None:
    matched_text = "please use uv run python and pytest"

    messages = build_preset_messages(
        user_input=matched_text,
        thread_id="session-2",
        turn_index=2,
        include_base_messages=False,
    )

    assert len(messages) >= 1
    assert isinstance(messages[0], SystemMessage)
    assert str(messages[0].content).strip()


def test_build_preset_messages_loads_multiple_lorebooks(monkeypatch, tmp_path: Path) -> None:
    lorebook_root = tmp_path / "lorebooks"
    _write_test_lorebook(lorebook_root, "lb-a", "trigger-a", "A content", order=20)
    _write_test_lorebook(lorebook_root, "lb-b", "trigger-b", "B content", order=5)

    monkeypatch.setattr(preset_module, "_LOREBOOK_ROOT", lorebook_root)
    monkeypatch.setattr(preset_module, "_ENGINES", {})

    messages = build_preset_messages(
        user_input="trigger-a and trigger-b",
        thread_id="multi-session",
        turn_index=1,
        lorebook_ids=["lb-a", "lb-b"],
        include_base_messages=False,
    )

    assert len(messages) == 1
    assert isinstance(messages[0], SystemMessage)
    text = str(messages[0].content)
    assert "B content" in text
    assert "A content" in text
    assert text.index("B content") < text.index("A content")


def test_build_preset_messages_uses_custom_character_prompt_path(tmp_path: Path) -> None:
    custom_prompt = tmp_path / "custom_role.md"
    custom_prompt.write_text("<character-information>\ncustom-role\n</character-information>", encoding="utf-8")

    messages = build_preset_messages(
        user_input="no-match-for-lorebook",
        thread_id="session-custom-role",
        turn_index=1,
        include_base_messages=True,
        character_prompt_path=str(custom_prompt),
    )

    human_messages = [msg for msg in messages if isinstance(msg, HumanMessage)]
    assert len(human_messages) == 1
    assert "custom-role" in str(human_messages[0].content)


def test_build_preset_messages_raises_for_missing_character_prompt() -> None:
    try:
        build_preset_messages(
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
