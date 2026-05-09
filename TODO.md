# Tools vs shell: mutating and risky operations

## Goal

Replace open-ended shell for **non-read-only and security-sensitive** workflows with **first-class tools**: typed parameters, path/workspace constraints, explicit semantics, and optional user confirmation. Keep shell for simple read-only introspection where the allowlist already matches intent.

Reference: `config/tool/default.yaml` (`safe_shell_commands`, `dangerous_shell_commands`) and `run_shell_command_popen_tool` in `tools/shell.py`.


# OpenAI-compatible HTTP API

## Goal

Expose this repo’s **LangGraph agent** (same runtime as the interactive CLI) over an **OpenAI-compatible** HTTP surface so clients can call it with standard SDKs and tools that expect:

- `POST /v1/chat/completions` (JSON and SSE streaming)
- `GET /v1/models` (optional but useful for discovery)

The **upstream** LLM is already OpenAI-schema compatible (`graphs/llm.py` uses `ChatOpenAI` / DeepSeek-style clients). This section is about serving **your agent** as the API, not proxying raw provider calls.