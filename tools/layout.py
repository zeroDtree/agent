from __future__ import annotations

import os
from pathlib import Path

from config.config_class import GraphConfig, WorkConfig
from config.sandbox import PathLayout, resolve_path_layout


def resolve_layout(work_config: WorkConfig, graph_config: GraphConfig) -> PathLayout:
    workspace = Path(work_config.working_directory).expanduser()
    if not workspace.is_absolute():
        workspace = (Path(os.getcwd()) / workspace).resolve()
    return resolve_path_layout(
        workspace,
        plan_directory=work_config.sandbox.plan_directory,
        thread_id=graph_config.thread_id,
        deny_read_globs=work_config.sandbox.deny_read_paths,
    )


def resolve_plan_dir(work_config: WorkConfig, graph_config: GraphConfig, *, create: bool = False) -> Path:
    plan_dir = resolve_layout(work_config, graph_config).plan_dir
    if create:
        plan_dir.mkdir(parents=True, exist_ok=True)
    return plan_dir
