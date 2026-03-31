from __future__ import annotations

from typing import Any


def _md(description: str) -> dict[str, Any]:
    """Standard metadata payload for dataclass fields."""
    return {"description": description}
