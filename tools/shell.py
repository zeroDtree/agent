import subprocess

from langchain_core.tools import tool

from config.config_class import WorkConfig


def get_run_shell_command_popen_tool(work_config: WorkConfig):

    @tool
    def run_shell_command_popen_tool(command: str) -> str:
        """Execute shell command with directory restrictions and path validation. Input a string command and return the command output."""
        try:

            # Execute command uniformly through shell
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=work_config.command_timeout,
                cwd=work_config.working_directory,
            )

            output = result.stdout
            if result.stderr:
                output += f"\nError: {result.stderr}"

            return output

        except subprocess.TimeoutExpired:
            error_msg = f"Command timeout: {command}"
            return error_msg

        except Exception as e:
            error_msg = f"Execution error: {str(e)}"
            return error_msg

    return run_shell_command_popen_tool
