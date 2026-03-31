import json
from pathlib import Path

from prompt_manager.builder import build_lorebook
from prompt_manager.loader import load_lorebook
from prompt_manager.runtime import LorebookRuntimeEngine
from prompt_manager.types import Lorebook, RuntimeContext


def _base_lorebook_dict() -> dict:
    return {
        "id": "test-lb",
        "name": "Test",
        "enabled": True,
        "description": "",
        "merge_strategy": "global_sorted_merge",
        "source_scope": ["global"],
        "merge_policy": {"mode": "global_sorted_merge", "priority": ["global"]},
        "budget": {"max_tokens": 2000, "overflow_policy": "drop_low_priority"},
        "defaults": {
            "position": "after_char_defs",
            "probability": 1.0,
            "case_sensitive": False,
        },
        "runtime": {
            "max_recursion_steps": 3,
            "random_seed_strategy": "session_stable",
            "log_level": "normal",
        },
        "entries": [],
    }


def _entry(
    eid: str,
    content: str,
    keywords: list[str],
    *,
    order: int = 100,
    inclusion_group: str | None = None,
    group_scoring: bool = False,
    probability: float = 1.0,
    max_tokens: int = 500,
    truncate: str = "tail",
) -> dict:
    return {
        "id": eid,
        "path": f"entries/{eid}.md",
        "enabled": True,
        "content": content,
        "resolved": {
            "triggers": {
                "keywords": keywords,
                "regex": [],
                "case_sensitive": False,
                "whole_word": False,
            },
            "filters": {
                "role_allowlist": [],
                "role_denylist": [],
            },
            "injection": {
                "position": "after_char_defs",
                "order": order,
                "message_type": None,
                "outlet": None,
                "depth": None,
            },
            "advanced": {
                "inclusion_group": inclusion_group,
                "group_scoring": group_scoring,
                "probability": probability,
                "recursive": False,
                "max_recursion_depth": 0,
                "sticky_turns": 0,
                "cooldown_turns": 0,
                "delay_turns": 0,
            },
            "budget": {"max_tokens": max_tokens, "truncate": truncate},
        },
    }


def _load_from_dict(data: dict, tmp_path: Path) -> Lorebook:
    path = tmp_path / "book.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return load_lorebook(path)


def test_build_and_run_runtime(tmp_path: Path) -> None:
    source = Path("prompts/lorebooks/coding-default")
    output = tmp_path / "lorebook.json"
    built = build_lorebook(source=source, output=output)
    assert built["id"] == "coding-default"
    assert output.exists()

    lorebook = load_lorebook(output)
    engine = LorebookRuntimeEngine(lorebook)
    context = RuntimeContext(
        request_id="req_1",
        session_id="sess_1",
        role="assistant",
        text="please run python script with pytest",
        tags={"coding", "python"},
        turn_index=1,
    )
    result = engine.run(context)
    assert "python-env-rule" in result.matched_entries
    assert result.injected_prompt
    assert result.events


def test_probability_reproducible_session_stable(tmp_path: Path) -> None:
    data = _base_lorebook_dict()
    data["entries"] = [
        _entry("prob-a", "body", ["trigger"], probability=0.42, order=10),
    ]
    lorebook = _load_from_dict(data, tmp_path)
    engine = LorebookRuntimeEngine(lorebook)
    ctx = RuntimeContext(
        request_id="req_same",
        session_id="sess_same",
        role="assistant",
        text="trigger word",
        tags=set(),
        turn_index=0,
    )
    r1 = engine.run(ctx)
    r2 = engine.run(ctx)
    assert r1.dropped_reasons.get("prob-a") == r2.dropped_reasons.get("prob-a")
    assert (r1.injected_entries == []) == (r2.injected_entries == [])


def test_inclusion_group_prefers_score_when_group_scoring(tmp_path: Path) -> None:
    data = _base_lorebook_dict()
    data["entries"] = [
        _entry(
            "low-order",
            "low wins on order only",
            ["aaa"],
            order=100,
            inclusion_group="g",
            group_scoring=False,
        ),
        _entry(
            "high-score",
            "high wins on match strength",
            ["bbb", "bbb", "bbb"],
            order=1,
            inclusion_group="g",
            group_scoring=True,
        ),
    ]
    data["entries"][1]["resolved"]["advanced"]["group_scoring"] = True
    data["entries"][0]["resolved"]["advanced"]["group_scoring"] = True
    lorebook = _load_from_dict(data, tmp_path)
    engine = LorebookRuntimeEngine(lorebook)
    ctx = RuntimeContext(
        request_id="r1",
        session_id="s1",
        role="assistant",
        text="aaa bbb bbb bbb",
        tags=set(),
        turn_index=0,
    )
    result = engine.run(ctx)
    assert "high-score" in result.injected_entries
    assert "low-order" not in result.injected_entries


def test_inclusion_group_uses_order_without_group_scoring(tmp_path: Path) -> None:
    data = _base_lorebook_dict()
    data["entries"] = [
        _entry("a", "x", ["t"], order=5, inclusion_group="g", group_scoring=False),
        _entry("b", "y", ["t"], order=10, inclusion_group="g", group_scoring=False),
    ]
    lorebook = _load_from_dict(data, tmp_path)
    engine = LorebookRuntimeEngine(lorebook)
    ctx = RuntimeContext(
        request_id="r1",
        session_id="s1",
        role="assistant",
        text="t",
        tags=set(),
        turn_index=0,
    )
    result = engine.run(ctx)
    assert result.injected_entries == ["a"]


def test_inclusion_group_great_first_prefers_larger_order(tmp_path: Path) -> None:
    data = _base_lorebook_dict()
    data["runtime"]["injection_order"] = "great_first"
    data["entries"] = [
        _entry("a", "x", ["t"], order=5, inclusion_group="g", group_scoring=False),
        _entry("b", "y", ["t"], order=10, inclusion_group="g", group_scoring=False),
    ]
    lorebook = _load_from_dict(data, tmp_path)
    engine = LorebookRuntimeEngine(lorebook)
    ctx = RuntimeContext(
        request_id="r1",
        session_id="s1",
        role="assistant",
        text="t",
        tags=set(),
        turn_index=0,
    )
    result = engine.run(ctx)
    assert result.injected_entries == ["b"]


def test_entry_truncate_tail(tmp_path: Path) -> None:
    long_body = " ".join(f"w{i}" for i in range(20))
    data = _base_lorebook_dict()
    data["entries"] = [
        _entry("trunc", long_body, ["go"], max_tokens=5, truncate="tail"),
    ]
    lorebook = _load_from_dict(data, tmp_path)
    engine = LorebookRuntimeEngine(lorebook)
    ctx = RuntimeContext(
        request_id="r1",
        session_id="s1",
        role="assistant",
        text="go",
        tags=set(),
        turn_index=0,
    )
    result = engine.run(ctx)
    words = result.injected_prompt.split()
    assert len(words) == 5
    assert result.injected_prompt.endswith("w19")


def test_merge_truncate_tail(tmp_path: Path) -> None:
    data = _base_lorebook_dict()
    data["budget"] = {"max_tokens": 7, "overflow_policy": "truncate_tail"}
    data["entries"] = [
        _entry("e1", "one two three four", ["x"], order=10, max_tokens=100),
        _entry("e2", "five six seven eight", ["x"], order=5, max_tokens=100),
    ]
    lorebook = _load_from_dict(data, tmp_path)
    engine = LorebookRuntimeEngine(lorebook)
    ctx = RuntimeContext(
        request_id="r1",
        session_id="s1",
        role="assistant",
        text="x",
        tags=set(),
        turn_index=0,
    )
    result = engine.run(ctx)
    assert len(result.injected_prompt.split()) == 7
    trunc_ev = [e for e in result.events if e.reason == "merged_lorebook_truncated"]
    assert len(trunc_ev) == 1


def test_expand_stage_recursively_adds_entries(tmp_path: Path) -> None:
    data = _base_lorebook_dict()
    data["entries"] = [
        _entry("seed", "nested_trigger appears", ["activate"], order=20),
        _entry("nested", "expanded body", ["nested_trigger"], order=10),
    ]
    data["entries"][0]["resolved"]["advanced"]["recursive"] = True

    lorebook = _load_from_dict(data, tmp_path)
    engine = LorebookRuntimeEngine(lorebook)
    ctx = RuntimeContext(
        request_id="r1",
        session_id="s1",
        role="assistant",
        text="activate",
        tags=set(),
        turn_index=0,
    )
    result = engine.run(ctx)

    assert "seed" in result.injected_entries
    assert "nested" in result.injected_entries
    assert any(e.stage == "expand" and e.reason == "expand_started" for e in result.events)
    assert any(e.stage == "expand" and e.reason == "expand_completed" for e in result.events)
    assert any(e.stage == "expand" and e.reason == "recursive_match" and e.entry_id == "nested" for e in result.events)


def test_lorebook_disabled_emits_event(tmp_path: Path) -> None:
    data = _base_lorebook_dict()
    data["enabled"] = False
    data["entries"] = [_entry("e", "c", ["z"])]
    lorebook = _load_from_dict(data, tmp_path)
    engine = LorebookRuntimeEngine(lorebook)
    ctx = RuntimeContext(
        request_id="r1",
        session_id="s1",
        role="assistant",
        text="z",
        tags=set(),
        turn_index=0,
    )
    result = engine.run(ctx)
    assert any(e.reason == "lorebook_disabled" for e in result.events)


def test_log_level_off_no_events(tmp_path: Path) -> None:
    raw = _base_lorebook_dict()
    raw["runtime"]["log_level"] = "off"
    raw["entries"] = [_entry("e", "c", ["z"])]
    lorebook = _load_from_dict(raw, tmp_path)
    engine = LorebookRuntimeEngine(lorebook)
    ctx = RuntimeContext(
        request_id="r1",
        session_id="s1",
        role="assistant",
        text="z",
        tags=set(),
        turn_index=0,
    )
    result = engine.run(ctx)
    assert result.events == []
