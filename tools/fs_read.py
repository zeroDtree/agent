from __future__ import annotations

import re

from langchain_core.tools import StructuredTool

from config.config_class import GraphConfig, WorkConfig
from tools.capability import CAPABILITY_METADATA_KEY, NEEDS_NETWORK_METADATA_KEY, ToolCapability
from tools.layout import resolve_layout
from tools.path_policy import is_denied_read_path, resolve_workspace_path

_MAX_READ_CHARS = 50_000
_MAX_GREP_MATCHES = 200


def get_fs_read_tools(work_config: WorkConfig, graph_config: GraphConfig) -> list[StructuredTool]:
    metadata = {
        CAPABILITY_METADATA_KEY: ToolCapability.RO.value,
        NEEDS_NETWORK_METADATA_KEY: False,
    }

    def list_dir(path: str = ".") -> str:
        """List files and directories under a workspace-relative path."""
        layout = resolve_layout(work_config, graph_config)
        target = resolve_workspace_path(layout.workspace, path)
        if is_denied_read_path(target, layout.deny_read_paths):
            return f"error: read denied for path: {path}"
        if not target.exists():
            return f"error: path does not exist: {path}"
        if target.is_file():
            return target.name
        entries = sorted(target.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
        lines = []
        for entry in entries[:500]:
            suffix = "/" if entry.is_dir() else ""
            lines.append(f"{entry.name}{suffix}")
        if len(entries) > 500:
            lines.append(f"[...truncated, {len(entries)} entries total]")
        return "\n".join(lines) if lines else "(empty)"

    def read_file(path: str, offset: int = 1, limit: int = 200) -> str:
        """Read a slice of a text file from the workspace."""
        layout = resolve_layout(work_config, graph_config)
        target = resolve_workspace_path(layout.workspace, path)
        if is_denied_read_path(target, layout.deny_read_paths):
            return f"error: read denied for path: {path}"
        if not target.is_file():
            return f"error: not a file: {path}"
        text = target.read_text(encoding="utf-8", errors="replace")
        if len(text) > _MAX_READ_CHARS:
            text = text[:_MAX_READ_CHARS] + f"\n[...truncated, {len(text)} chars total]"
        lines = text.splitlines()
        start = max(offset - 1, 0)
        end = start + max(limit, 1)
        selected = lines[start:end]
        numbered = [f"{start + index + 1}: {line}" for index, line in enumerate(selected)]
        return "\n".join(numbered) if numbered else "(empty)"

    def grep(pattern: str, path: str = ".", ignore_case: bool = False) -> str:
        """Search for a regex pattern in workspace files."""
        layout = resolve_layout(work_config, graph_config)
        root = resolve_workspace_path(layout.workspace, path)
        if is_denied_read_path(root, layout.deny_read_paths):
            return f"error: read denied for path: {path}"
        flags = re.IGNORECASE if ignore_case else 0
        try:
            compiled = re.compile(pattern, flags)
        except re.error as error:
            return f"error: invalid regex: {error}"

        matches: list[str] = []
        files = [root] if root.is_file() else [p for p in root.rglob("*") if p.is_file()]
        for file_path in files:
            if is_denied_read_path(file_path, layout.deny_read_paths):
                continue
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            relative = file_path.relative_to(layout.workspace)
            for line_number, line in enumerate(text.splitlines(), start=1):
                if compiled.search(line):
                    matches.append(f"{relative}:{line_number}:{line}")
                    if len(matches) >= _MAX_GREP_MATCHES:
                        matches.append(f"[...truncated at {_MAX_GREP_MATCHES} matches]")
                        return "\n".join(matches)
        return "\n".join(matches) if matches else "(no matches)"

    return [
        StructuredTool.from_function(list_dir, metadata=metadata),
        StructuredTool.from_function(read_file, metadata=metadata),
        StructuredTool.from_function(grep, metadata=metadata),
    ]
