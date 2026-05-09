# Tools vs shell: mutating and risky operations

## Goal

Replace open-ended shell for **non-read-only and security-sensitive** workflows with **first-class tools**: typed parameters, path/workspace constraints, explicit semantics, and optional user confirmation. Keep shell for simple read-only introspection where the allowlist already matches intent.

Reference: `config/tool/default.yaml` (`safe_shell_commands`, `dangerous_shell_commands`) and `run_shell_command_popen_tool` in `tools/shell.py`.