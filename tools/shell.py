import os
import subprocess
from pathlib import Path

from langchain_core.tools import tool

from config.config_class import WorkConfig

_MAX_OUTPUT_CHARS = 20_000


def get_run_shell_command_popen_tool(work_config: WorkConfig):
    working_dir = Path(work_config.working_directory).expanduser()
    if not working_dir.is_absolute():
        working_dir = (Path(os.getcwd()) / working_dir).resolve()
    working_dir_text = str(working_dir)
    tool_description = (
        "Execute a shell command and return its output.\n\n"
        f"Shell commands start in this working directory: {working_dir_text}.\n"
        "Relative paths in command strings are resolved from that directory.\n"
        "This directory is independent from Python/uv virtual environment paths.\n\n"
        "Returns a structured result containing exit code, stdout, and stderr so "
        "the caller can distinguish between successful and failed executions."
    )

    @tool(description=tool_description)
    def run_shell_command_popen_tool(command: str) -> str:
        """Execute a shell command and return stdout/stderr (see tool description for cwd)."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=work_config.command_timeout,
                cwd=str(working_dir),
            )

            stdout = result.stdout
            stderr = result.stderr

            if len(stdout) > _MAX_OUTPUT_CHARS:
                stdout = stdout[:_MAX_OUTPUT_CHARS] + f"\n[...truncated, {len(stdout)} chars total]"
            if len(stderr) > _MAX_OUTPUT_CHARS:
                stderr = stderr[:_MAX_OUTPUT_CHARS] + f"\n[...truncated, {len(stderr)} chars total]"

            parts = [f"exit_code: {result.returncode}"]
            if stdout:
                parts.append(f"stdout:\n{stdout}")
            if stderr:
                parts.append(f"stderr:\n{stderr}")

            return "\n".join(parts)

        except subprocess.TimeoutExpired:
            return f"exit_code: -1\nerror: command timed out after {work_config.command_timeout}s\ncommand: {command}"

        except Exception as e:
            return f"exit_code: -1\nerror: {e}\ncommand: {command}"

    return run_shell_command_popen_tool
