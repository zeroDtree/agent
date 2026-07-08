from __future__ import annotations

import json
from typing import Any


def tool_call_field(tool_call: Any, field: str, default: Any = "") -> Any:
    if isinstance(tool_call, dict):
        return tool_call.get(field, default)
    return getattr(tool_call, field, default)


def tool_calls_payload(message: Any) -> list[dict[str, Any]]:
    raw = getattr(message, "tool_calls", None)
    if not raw:
        return []
    out: list[dict[str, Any]] = []
    for tc in raw:
        if isinstance(tc, dict):
            out.append(
                {
                    "name": tc.get("name"),
                    "args": tc.get("args"),
                    "id": tc.get("id"),
                }
            )
        else:
            out.append(
                {
                    "name": getattr(tc, "name", None),
                    "args": getattr(tc, "args", None),
                    "id": getattr(tc, "id", None),
                }
            )
    return out


def format_tool_call_args(args: Any) -> str:
    if args is None:
        return "{}"
    if isinstance(args, str):
        return args
    try:
        return json.dumps(args, ensure_ascii=False)
    except TypeError:
        return str(args)


def format_tool_call_line(name: str, args: Any) -> str:
    return f"→ tool {name} {format_tool_call_args(args)}"


def format_tool_calls_summary(message: Any) -> str:
    lines: list[str] = []
    for tc in tool_calls_payload(message):
        raw_name = tc.get("name")
        if raw_name is None or not str(raw_name).strip():
            continue
        lines.append(f"  {format_tool_call_line(str(raw_name), tc.get('args'))}")
    return "\n".join(lines) if lines else "  (no tool calls)"
