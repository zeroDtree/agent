"""Plain-text CLI helpers; MCP status uses tabulate for aligned tables."""

from __future__ import annotations

import re
from typing import Any

import yaml
from tabulate import tabulate

# Match credential-like key *names*. Avoid bare "token" — it matches max_tokens, etc.
_CREDENTIAL_KEY_RE = re.compile(
    r"(api[_-]?key|client[_-]?secret|secret|password|authorization|bearer|credential)",
    re.IGNORECASE,
)


def _is_sensitive_key(key: str) -> bool:
    k = key.lower()
    # Plural / limit-style keys (not secrets).
    if k.endswith("_tokens"):
        return False
    if k == "token" or k.endswith("_token"):
        return True
    return bool(_CREDENTIAL_KEY_RE.search(k))


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
    print(
        yaml.dump(
            data,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        ),
        end="",
    )
    print()


def print_mcp_servers_status(rows: list[tuple[str, int, str]]) -> None:
    """Print MCP load summary: server name, tool count, status text."""
    print("\n=== MCP servers ===")
    if not rows:
        print(tabulate([], headers=["Server", "Tools", "Status"], tablefmt="fancy_grid"))
        print("  (none)")
        print()
        return
    body = [[name, n_tools, status] for name, n_tools, status in rows]
    print(
        tabulate(
            body,
            headers=["Server", "Tools", "Status"],
            tablefmt="fancy_grid",
            colalign=("left", "right", "left"),
        )
    )
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
