import json
from pathlib import Path

from prompt_manager.loader import load_lorebook
from prompt_manager.runtime import LorebookRuntimeEngine, MultiLorebookRuntimeEngine
from prompt_manager.types import Lorebook, RuntimeContext


def _make_lorebook_payload(lorebook_id: str, keyword: str, content: str, order: int) -> dict:
    return {
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
                "id": "entry",
                "path": "entries/entry.md",
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


def _write_and_load_lorebook(tmp_path: Path, payload: dict) -> Lorebook:
    path = tmp_path / f"{payload['id']}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return load_lorebook(path)


def test_multi_lorebook_runtime_global_sort_after_filter(tmp_path: Path) -> None:
    lorebook_a = _write_and_load_lorebook(tmp_path, _make_lorebook_payload("lb-a", "alpha", "A body", order=20))
    lorebook_b = _write_and_load_lorebook(tmp_path, _make_lorebook_payload("lb-b", "beta", "B body", order=5))
    runtime = MultiLorebookRuntimeEngine([LorebookRuntimeEngine(lorebook_a), LorebookRuntimeEngine(lorebook_b)])

    context = RuntimeContext(
        request_id="req-1",
        session_id="sess-1",
        role="assistant",
        text="alpha beta",
        tags={"coding"},
        turn_index=1,
    )
    result = runtime.run(context)

    assert "B body" in result.injected_prompt
    assert "A body" in result.injected_prompt
    assert result.injected_prompt.index("B body") < result.injected_prompt.index("A body")
    assert "lb-a:entry" in result.injected_entries
    assert "lb-b:entry" in result.injected_entries
