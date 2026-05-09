"""Plain-text CLI helpers (no Rich)."""

from __future__ import annotations

import pprint
import re
from typing import Any

_SENSITIVE_KEY_RE = re.compile(
    r"(api[_-]?key|secret|password|token|authorization|bearer|credential)",
    re.IGNORECASE,
)


def _is_sensitive_key(key: str) -> bool:
    return bool(_SENSITIVE_KEY_RE.search(key))


def redact_sensitive_mapping(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            str(k): "***REDACTED***" if _is_sensitive_key(str(k)) else redact_sensitive_mapping(v)
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [redact_sensitive_mapping(item) for item in obj]
    if isinstance(obj, tuple):
        return tuple(redact_sensitive_mapping(item) for item in obj)
    return obj


def print_config_block(title: str, data: Any) -> None:
    print(f"\n=== {title} ===")
    pprint.pprint(data, width=100, compact=False)
    print()


def print_mcp_servers_status(rows: list[tuple[str, int, str]]) -> None:
    """Print MCP load summary: server name, tool count, status text."""
    print("\n=== MCP servers ===")
    if not rows:
        print("  (none)")
        print()
        return
    name_w = max(len(r[0]) for r in rows)
    for name, n_tools, status in rows:
        print(f"  {name:<{name_w}}  tools={n_tools:<4}  {status}")
    print()


def print_lorebook_injections(
    entries: list[tuple[str, int | None, int | None]],
) -> None:
    if not entries:
        return
    print("\n--- Lorebook injections (this turn) ---")
    for entry_id, order, depth in entries:
        o = "—" if order is None else str(order)
        d = "—" if depth is None else str(depth)
        print(f"  {entry_id}  order={o}  depth={d}")
    print()
