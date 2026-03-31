from __future__ import annotations

import importlib.util
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict


def _load_kg_module() -> Any:
    root = Path(__file__).resolve().parents[1]
    module_path = root / "mcp" / "knowledge_graph.py"
    spec = importlib.util.spec_from_file_location("kg_module", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module spec from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _print_step(name: str, payload: Dict[str, Any]) -> None:
    print(f"=== {name} ===")
    print(json.dumps(payload, ensure_ascii=True, indent=2))


def _assert_success(name: str, payload: Dict[str, Any]) -> None:
    if not payload.get("success"):
        _print_step(name, payload)
        raise RuntimeError(f"{name} failed: {payload.get('message')}")


def main() -> int:
    kg = _load_kg_module()

    health = kg.health_check()
    _print_step("health_check", health)
    _assert_success("health_check", health)

    token = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    subject = f"test_subject_{token}"
    relation = "KNOWS"
    obj = f"test_object_{token}"
    _print_step("test_payload", {"subject": subject, "relation": relation, "obj": obj})

    add_res = kg.add_memory(subject, relation, obj)
    _print_step("add_memory", add_res)
    _assert_success("add_memory", add_res)

    memories = kg.get_memories_for_subject(subject)
    _print_step("get_memories_for_subject", memories)
    _assert_success("get_memories_for_subject", memories)

    search_res = kg.search_entities(subject)
    _print_step("search_entities", search_res)
    _assert_success("search_entities", search_res)

    neighbors = kg.get_neighbors(subject, depth=1)
    _print_step("get_neighbors", neighbors)
    _assert_success("get_neighbors", neighbors)

    dry_run_before = kg.delete_memory(subject, relation, obj, dry_run=True)
    _print_step("delete_memory_dry_run_before", dry_run_before)
    _assert_success("delete_memory_dry_run_before", dry_run_before)

    delete_res = kg.delete_memory(subject, relation, obj, dry_run=False)
    _print_step("delete_memory", delete_res)
    _assert_success("delete_memory", delete_res)

    dry_run_after = kg.delete_memory(subject, relation, obj, dry_run=True)
    _print_step("delete_memory_dry_run_after", dry_run_after)
    _assert_success("delete_memory_dry_run_after", dry_run_after)

    print("Knowledge graph end-to-end test passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Knowledge graph test failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
