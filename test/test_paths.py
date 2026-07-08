from __future__ import annotations

from pathlib import Path

import pytest

from zdt_agent.paths import config_dir, repo_root


def test_repo_root_has_project_marker() -> None:
    root = repo_root()
    assert (root / ".project-root").is_file()


def test_repo_root_from_arbitrary_cwd(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir("/tmp")
    repo_root.cache_clear()
    root = repo_root()
    assert (root / ".project-root").is_file()
    assert (root / "config" / "config.yaml").is_file()


def test_config_dir_falls_back_to_repo_when_cwd_has_no_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = repo_root()
    work_dir = root / "work_dir"
    work_dir.mkdir(exist_ok=True)
    monkeypatch.chdir(work_dir)
    assert config_dir() == root / "config"


def test_config_dir_uses_cwd_when_config_exists(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    local_config = tmp_path / "config"
    local_config.mkdir()
    (local_config / "config.yaml").write_text("defaults: []\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert config_dir() == local_config
