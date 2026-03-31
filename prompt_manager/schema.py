from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

_REPO_ROOT = Path(__file__).resolve().parents[1]


def lorebook_schema_path() -> Path:
    """Resolve `schemas/lorebook.schema.json` relative to the repository root."""
    return _REPO_ROOT / "schemas" / "lorebook.schema.json"


def load_lorebook_schema(schema_path: Path | None = None) -> dict[str, Any]:
    path = schema_path or lorebook_schema_path()
    return json.loads(path.read_text(encoding="utf-8"))


def validate_lorebook_json(data: dict[str, Any], schema_path: Path | None = None) -> None:
    """Validate a lorebook dict against the JSON Schema; raises on failure."""
    schema = load_lorebook_schema(schema_path)
    Draft202012Validator(schema).validate(data)
