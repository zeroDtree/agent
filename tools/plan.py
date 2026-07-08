from __future__ import annotations

from langchain_core.tools import StructuredTool

from config.config_class import GraphConfig, WorkConfig
from tools.capability import CAPABILITY_METADATA_KEY, NEEDS_NETWORK_METADATA_KEY, ToolCapability
from tools.layout import resolve_plan_dir
from tools.path_policy import PathPolicyError, resolve_plan_path

_MAX_PLAN_CHARS = 200_000


def _plan_filename(filename: str) -> str:
    return filename if filename.endswith(".md") else f"{filename}.md"


def get_plan_tools(work_config: WorkConfig, graph_config: GraphConfig) -> list[StructuredTool]:
    metadata = {
        CAPABILITY_METADATA_KEY: ToolCapability.RW_PLAN.value,
        NEEDS_NETWORK_METADATA_KEY: False,
    }

    def list_plans() -> str:
        """List plan files in the current session plan directory."""
        plan_dir = resolve_plan_dir(work_config, graph_config)
        files = sorted(path.name for path in plan_dir.glob("*.md"))
        return "\n".join(files) if files else "(no plan files)"

    def read_plan(filename: str) -> str:
        """Read a plan file from the session plan directory."""
        try:
            plan_dir = resolve_plan_dir(work_config, graph_config)
            target = resolve_plan_path(plan_dir, _plan_filename(filename))
            if not target.is_file():
                return f"error: plan file not found: {filename}"
            return target.read_text(encoding="utf-8")
        except PathPolicyError as error:
            return f"error: {error}"

    def write_plan(filename: str, content: str) -> str:
        """Create or overwrite a plan file in the session plan directory."""
        if len(content) > _MAX_PLAN_CHARS:
            return f"error: content exceeds {_MAX_PLAN_CHARS} characters"
        try:
            plan_dir = resolve_plan_dir(work_config, graph_config, create=True)
            target = resolve_plan_path(plan_dir, _plan_filename(filename))
            target.write_text(content, encoding="utf-8")
            return f"ok: wrote plan {target.name}"
        except PathPolicyError as error:
            return f"error: {error}"

    def append_plan(filename: str, content: str) -> str:
        """Append content to a plan file in the session plan directory."""
        if len(content) > _MAX_PLAN_CHARS:
            return f"error: content exceeds {_MAX_PLAN_CHARS} characters"
        try:
            plan_dir = resolve_plan_dir(work_config, graph_config, create=True)
            target = resolve_plan_path(plan_dir, _plan_filename(filename))
            existing = target.read_text(encoding="utf-8") if target.exists() else ""
            target.write_text(existing + content, encoding="utf-8")
            return f"ok: appended to plan {target.name}"
        except PathPolicyError as error:
            return f"error: {error}"

    def apply_plan_patch(filename: str, old_text: str, new_text: str) -> str:
        """Replace old_text with new_text once in a plan file."""
        try:
            plan_dir = resolve_plan_dir(work_config, graph_config, create=True)
            target = resolve_plan_path(plan_dir, _plan_filename(filename))
            if not target.is_file():
                return f"error: plan file not found: {filename}"
            current = target.read_text(encoding="utf-8")
            if old_text not in current:
                return "error: old_text not found in plan file"
            updated = current.replace(old_text, new_text, 1)
            if len(updated) > _MAX_PLAN_CHARS:
                return f"error: patched content exceeds {_MAX_PLAN_CHARS} characters"
            target.write_text(updated, encoding="utf-8")
            return f"ok: patched plan {target.name}"
        except PathPolicyError as error:
            return f"error: {error}"

    return [
        StructuredTool.from_function(list_plans, metadata=metadata),
        StructuredTool.from_function(read_plan, metadata=metadata),
        StructuredTool.from_function(write_plan, metadata=metadata),
        StructuredTool.from_function(append_plan, metadata=metadata),
        StructuredTool.from_function(apply_plan_patch, metadata=metadata),
    ]
