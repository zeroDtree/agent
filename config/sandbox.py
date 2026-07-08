from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class WorkMode(Enum):
    RO = "ro"
    SW = "sw"
    AW = "aw"
    PL = "pl"


@dataclass(frozen=True)
class SandboxProfile:
    """Filesystem sandbox policy. Does not encode network access."""

    readonly: bool
    read_paths: tuple[Path, ...]
    write_paths: tuple[Path, ...]
    deny_read_paths: tuple[Path, ...] = ()


@dataclass(frozen=True)
class NetworkPolicy:
    """Independent outbound network switch."""

    enabled: bool = False
    allowlist: tuple[str, ...] = ()


@dataclass(frozen=True)
class SandboxSettings:
    plan_directory: str = ".agent/plans"
    deny_read_paths: tuple[str, ...] = (".env",)


@dataclass(frozen=True)
class PathLayout:
    workspace: Path
    plan_dir: Path
    deny_read_paths: tuple[Path, ...]


def resolve_path_layout(
    working_directory: str | Path,
    *,
    plan_directory: str,
    thread_id: str,
    deny_read_globs: tuple[str, ...],
) -> PathLayout:
    workspace = Path(working_directory).expanduser().resolve()
    plan_dir = (workspace / plan_directory / thread_id).resolve()
    deny_paths: list[Path] = []
    for pattern in deny_read_globs:
        if pattern == ".env":
            deny_paths.append((workspace / ".env").resolve())
        elif pattern == "**/.env":
            for candidate in workspace.rglob(".env"):
                if candidate.is_file():
                    deny_paths.append(candidate.resolve())
    return PathLayout(workspace=workspace, plan_dir=plan_dir, deny_read_paths=tuple(deny_paths))


def shell_profile_for_mode(work_mode: WorkMode, layout: PathLayout) -> SandboxProfile:
    if work_mode == WorkMode.AW:
        return SandboxProfile(
            readonly=False,
            read_paths=(layout.workspace,),
            write_paths=(layout.workspace,),
            deny_read_paths=layout.deny_read_paths,
        )
    return SandboxProfile(
        readonly=True,
        read_paths=(layout.workspace,),
        write_paths=(),
        deny_read_paths=layout.deny_read_paths,
    )


def plan_write_profile(layout: PathLayout) -> SandboxProfile:
    return SandboxProfile(
        readonly=False,
        read_paths=(layout.plan_dir,),
        write_paths=(layout.plan_dir,),
        deny_read_paths=(),
    )
