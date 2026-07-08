from __future__ import annotations

import os
import subprocess
from pathlib import Path

from langchain_core.tools import StructuredTool

from ..config.config_class import GraphConfig, WorkConfig
from ..config.sandbox import WorkMode, resolve_path_layout, shell_profile_for_mode
from ..sandbox.runner import get_sandbox_runner
from .capability import CAPABILITY_METADATA_KEY, NEEDS_NETWORK_METADATA_KEY, ToolCapability

_MAX_OUTPUT_CHARS = 20_000


def _workspace_for(work_config: WorkConfig) -> Path:
    working_dir = Path(work_config.working_directory).expanduser()
    if not working_dir.is_absolute():
        working_dir = (Path(os.getcwd()) / working_dir).resolve()
    return working_dir


def _format_result(returncode: int, stdout: str, stderr: str) -> str:
    if len(stdout) > _MAX_OUTPUT_CHARS:
        stdout = stdout[:_MAX_OUTPUT_CHARS] + f"\n[...truncated, {len(stdout)} chars total]"
    if len(stderr) > _MAX_OUTPUT_CHARS:
        stderr = stderr[:_MAX_OUTPUT_CHARS] + f"\n[...truncated, {len(stderr)} chars total]"
    parts = [f"exit_code: {returncode}"]
    if stdout:
        parts.append(f"stdout:\n{stdout}")
    if stderr:
        parts.append(f"stderr:\n{stderr}")
    return "\n".join(parts)


def _run_command(
    work_config: WorkConfig,
    graph_config: GraphConfig,
    command: str,
    *,
    readonly: bool,
) -> str:
    workspace = _workspace_for(work_config)
    layout = resolve_path_layout(
        workspace,
        plan_directory=work_config.sandbox.plan_directory,
        thread_id=graph_config.thread_id,
        deny_read_globs=work_config.sandbox.deny_read_paths,
    )
    if readonly:
        profile = shell_profile_for_mode(WorkMode.RO, layout)
    else:
        profile = shell_profile_for_mode(WorkMode.AW, layout)

    try:
        runner = get_sandbox_runner()
        result = runner.run(
            ["/bin/sh", "-c", command],
            profile,
            work_config.network,
            cwd=workspace,
            timeout=work_config.command_timeout,
        )
        return _format_result(result.returncode, result.stdout, result.stderr)
    except subprocess.TimeoutExpired:
        return f"exit_code: -1\nerror: command timed out after {work_config.command_timeout}s\ncommand: {command}"
    except Exception as error:
        return f"exit_code: -1\nerror: {error}\ncommand: {command}"


def get_shell_tools(work_config: WorkConfig, graph_config: GraphConfig) -> list[StructuredTool]:
    workspace_text = str(_workspace_for(work_config))
    ro_description = (
        "Execute a read-only shell command in a sandbox and return its output.\n\n"
        f"Commands start in: {workspace_text}\n"
        "Filesystem writes inside the workspace are blocked by the sandbox."
    )
    rw_description = (
        "Execute a shell command with workspace write access in a sandbox and return its output.\n\n"
        f"Commands start in: {workspace_text}\n"
        "Only available in AW (any-write) work mode."
    )

    def run_shell_readonly(command: str) -> str:
        """Execute a read-only sandboxed shell command (see tool description for cwd)."""
        return _run_command(work_config, graph_config, command, readonly=True)

    def run_shell(command: str) -> str:
        """Execute a sandboxed shell command with workspace write access (see tool description)."""
        return _run_command(work_config, graph_config, command, readonly=False)

    return [
        StructuredTool.from_function(
            run_shell_readonly,
            description=ro_description,
            metadata={
                CAPABILITY_METADATA_KEY: ToolCapability.SHELL_RO.value,
                NEEDS_NETWORK_METADATA_KEY: True,
            },
        ),
        StructuredTool.from_function(
            run_shell,
            description=rw_description,
            metadata={
                CAPABILITY_METADATA_KEY: ToolCapability.SHELL_RW.value,
                NEEDS_NETWORK_METADATA_KEY: True,
            },
        ),
    ]
