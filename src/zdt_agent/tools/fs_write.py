from __future__ import annotations

from langchain_core.tools import StructuredTool

from ..config.config_class import GraphConfig, WorkConfig
from .capability import CAPABILITY_METADATA_KEY, NEEDS_NETWORK_METADATA_KEY, ToolCapability
from .layout import resolve_layout
from .path_policy import PathPolicyError, is_denied_read_path, resolve_workspace_path

_MAX_WRITE_CHARS = 500_000


def get_fs_write_tools(work_config: WorkConfig, graph_config: GraphConfig) -> list[StructuredTool]:
    metadata = {
        CAPABILITY_METADATA_KEY: ToolCapability.RW.value,
        NEEDS_NETWORK_METADATA_KEY: False,
    }

    def write_file(path: str, content: str) -> str:
        """Create or overwrite a file inside the workspace."""
        if len(content) > _MAX_WRITE_CHARS:
            return f"error: content exceeds {_MAX_WRITE_CHARS} characters"
        try:
            layout = resolve_layout(work_config, graph_config)
            target = resolve_workspace_path(layout.workspace, path)
            if is_denied_read_path(target, layout.deny_read_paths):
                return f"error: write denied for path: {path}"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return f"ok: wrote {len(content)} characters to {path}"
        except PathPolicyError as error:
            return f"error: {error}"

    def apply_patch(path: str, old_text: str, new_text: str) -> str:
        """Replace old_text with new_text in a workspace file."""
        try:
            layout = resolve_layout(work_config, graph_config)
            target = resolve_workspace_path(layout.workspace, path)
            if is_denied_read_path(target, layout.deny_read_paths):
                return f"error: write denied for path: {path}"
            if not target.is_file():
                return f"error: not a file: {path}"
            current = target.read_text(encoding="utf-8")
            if old_text not in current:
                return "error: old_text not found in file"
            updated = current.replace(old_text, new_text, 1)
            target.write_text(updated, encoding="utf-8")
            return f"ok: patched {path}"
        except PathPolicyError as error:
            return f"error: {error}"

    def create_directory(path: str) -> str:
        """Create a directory inside the workspace."""
        try:
            layout = resolve_layout(work_config, graph_config)
            target = resolve_workspace_path(layout.workspace, path)
            if is_denied_read_path(target, layout.deny_read_paths):
                return f"error: write denied for path: {path}"
            target.mkdir(parents=True, exist_ok=True)
            return f"ok: created directory {path}"
        except PathPolicyError as error:
            return f"error: {error}"

    return [
        StructuredTool.from_function(write_file, metadata=metadata),
        StructuredTool.from_function(apply_patch, metadata=metadata),
        StructuredTool.from_function(create_directory, metadata=metadata),
    ]
