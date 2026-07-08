from __future__ import annotations

from pathlib import Path


class PathPolicyError(PermissionError):
    pass


def resolve_workspace_path(workspace: Path, relative_path: str) -> Path:
    workspace = workspace.resolve()
    candidate = Path(relative_path).expanduser()
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (workspace / candidate).resolve()
    if resolved != workspace and workspace not in resolved.parents:
        raise PathPolicyError(f"Path escapes workspace: {relative_path}")
    return resolved


def resolve_plan_path(plan_dir: Path, filename: str) -> Path:
    plan_dir = plan_dir.resolve()
    name = Path(filename).name
    if not name or name in {".", ".."}:
        raise PathPolicyError(f"Invalid plan filename: {filename}")
    resolved = (plan_dir / name).resolve()
    if plan_dir not in resolved.parents and resolved != plan_dir:
        raise PathPolicyError(f"Plan path escapes plan directory: {filename}")
    return resolved


def is_denied_read_path(path: Path, deny_read_paths: tuple[Path, ...]) -> bool:
    resolved = path.resolve()
    return any(resolved == denied or denied in resolved.parents for denied in deny_read_paths)
