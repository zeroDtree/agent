"""Canonical paths for repo resources and runtime writable data."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

_PROJECT_ROOT_MARKER = ".project-root"
_PKG_DIR = Path(__file__).resolve().parent


def runtime_root() -> Path:
    return Path.cwd().resolve()


def _find_project_root(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        if (candidate / _PROJECT_ROOT_MARKER).is_file():
            return candidate
    return None


@lru_cache
def repo_root() -> Path:
    if env := os.environ.get("AGENT_REPO_ROOT"):
        return Path(env).expanduser().resolve()
    if found := _find_project_root(_PKG_DIR):
        return found
    raise FileNotFoundError(f"{_PROJECT_ROOT_MARKER} not found above package")


def _resolve(name: str) -> Path:
    direct = runtime_root() / name
    if direct.is_dir():
        return direct
    return repo_root() / name


def config_dir() -> Path:
    return _resolve("config")


def prompts_dir() -> Path:
    return _resolve("prompts")


def schema_dir() -> Path:
    return _resolve("schemas")
