# Agent

A LangGraph-based agent runtime with MCP integration, shell tooling, configurable tool approval modes, optional embedding-based retrieval, and a prompt manager.

## 1. Table of Contents

- [Agent](#agent)
  - [1. Table of Contents](#1-table-of-contents)
  - [2. What This Project Provides](#2-what-this-project-provides)
  - [3. Quick Start](#3-quick-start)
    - [3.1. Environment Variables](#31-environment-variables)
    - [3.2. Prerequisites](#32-prerequisites)
    - [3.3. Clone and Initialize](#33-clone-and-initialize)
    - [3.4. Run on Host](#34-run-on-host)
    - [3.5. Run in Docker](#35-run-in-docker)
    - [3.6. Common Startup Overrides](#36-common-startup-overrides)
    - [3.7. Interactive CLI commands](#37-interactive-cli-commands)
  - [4. Configuration](#4-configuration)
    - [4.1. Optional Environment Variables](#41-optional-environment-variables)
    - [4.2. Hydra Config Map](#42-hydra-config-map)
    - [4.3. MCP Runtime Model](#43-mcp-runtime-model)
  - [5. Work Mode and Policy Reference](#5-work-mode-and-policy-reference)
  - [6. Tooling Model](#6-tooling-model)
    - [6.1. Local Built-In Tools](#61-local-built-in-tools)
    - [6.2. MCP-Discovered Tools](#62-mcp-discovered-tools)
    - [6.3. Add a New Local Tool](#63-add-a-new-local-tool)
  - [7. Further Documentation](#7-further-documentation)

## 2. What This Project Provides

- **Stateful agent runtime**: Uses LangGraph with in-memory conversation state and streaming output.
- **5-level tool approval policy**: Ranges from fully manual to fully automatic (`work.tool_approval`).
- **MCP tool federation**: Loads tools from configured MCP servers; unavailable servers are skipped.
- **Shell command tool**: Executes commands with configurable timeout and working directory.
- **Embedding Knowledge Base (EKB)**: Supports semantic retrieval over indexed files.
- **Prompt manager** (`prompt_manager/`): Builds lorebook JSON from `prompts/lorebooks/*/entries/*.md` (or loads existing JSON), then each turn runs match → filter → expand → sort → budgeted inject, and splices the result into the preset skeleton (core, character, persona, and optional depth anchors). See [doc/prompt_manager.md](doc/prompt_manager.md).
- **Hydra-based configuration**: Hierarchical YAML composition with command-line overrides.
- **Container support**: Includes Docker scripts for build and startup.

## 3. Quick Start

### 3.1. Environment Variables

Set these variables before starting the agent.

Required for LLM requests:

| Variable       | Required | Description                                                              |
| -------------- | -------- | ------------------------------------------------------------------------ |
| `LLM_API_KEY`  | Yes      | API key used by `config/llm/default.yaml`.                               |
| `LLM_API_BASE` | Yes      | Base URL used by `config/llm/default.yaml` (provider-compatible endpoint). |

Example:

```bash
export LLM_API_KEY="your_api_key"
export LLM_API_BASE="https://your-provider.example/v1"
```

### 3.2. Prerequisites

- Install [uv](https://github.com/astral-sh/uv).
- Ensure required ports for MCP servers are available (default: `8000`, `8001`, `8002`).

### 3.3. Clone and Initialize

```bash
git clone git@github.com:zeroDtree/agent.git
cd agent
git submodule update --init --recursive
```

The `mcp` submodule contains MCP server implementations used by the startup scripts.

### 3.4. Run on Host

```bash
bash shell_scripts/start.sh [hydra overrides...]
```

This command starts MCP servers defined in `mcp/config.yaml`, waits for ports to become ready, then launches the agent. MCP servers are stopped when the process exits.

### 3.5. Run in Docker

```bash
bash shell_scripts/build_docker.sh
bash shell_scripts/start.docker.sh [hydra overrides...]
```

The container mounts:

- Project directory: `/tmp/proj_dir`
- Writable working directory: `/tmp/work_dir`
- `shell_scripts/start.sh` auto-creates `/tmp/work_dir/.venv` when `++work.working_directory=/tmp/work_dir` is set.

In Docker, use this split as a best practice:

- Read source files from `/tmp/proj_dir` (mounted project root).
- Write generated artifacts to `/tmp/work_dir` (mounted writable workspace).
- Keep task-level Python dependencies in `/tmp/work_dir/.venv`.

### 3.6. Common Startup Overrides

Use Hydra override syntax to customize runtime behavior at launch:

```bash
bash shell_scripts/start.sh \
  ++work.tool_approval=whitelist_accept \
  ++work.working_directory=/tmp/work_dir
```

When `++work.working_directory` is set to a non-`.` path, startup initializes a dedicated `.venv` under that directory once. This task-level environment is separate from `UV_PROJECT` (the runtime environment used to launch `main.py`).

### 3.7. Interactive CLI commands

After `bash shell_scripts/start.sh` (or `bash shell_scripts/start.docker.sh` in Docker), the CLI prompt accepts the following. Any other line is sent to the model as a normal user turn; each turn may print lorebook entries that matched for that message.

| Command                    | Description                                                                                                                                                            |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `exit` / `quit`            | Exit the CLI.                                                                                                                                                          |
| `!help`                    | Print this command summary.                                                                                                                                            |
| `!mode`                    | Show current work mode (`ro`, `sw`, `aw`, `pl`).                                                                                                                       |
| `!mode <ro\|sw\|aw\|pl>`   | Switch work mode (AW prompts for confirmation).                                                                                                                          |
| `!network`                 | Show whether outbound network is enabled.                                                                                                                              |
| `!network on\|off`         | Enable or disable outbound network (on prompts for confirmation).                                                                                                        |
| `!tool list`               | List tools available in the current work mode.                                                                                                                         |
| `!tool <name> [json_args]` | Invoke a tool with JSON arguments (defaults to `{}` if omitted).                                                                                                       |
| `!char list`               | List character roles from the configured role prompt directory (`char.prompt_dir`, default `prompts/chars`).                                                           |
| `!char show`               | Show the active role and its prompt file path.                                                                                                                         |
| `!char set <role>`         | Switch the active role for subsequent turns.                                                                                                                           |
| `!save <filename>`         | Save the conversation to JSON. Bare filenames are resolved under `conversation_dir` from chat config; absolute paths or paths with a parent segment are used as given. |
| `!load <filename>`         | Load conversation JSON from disk (same path rules as `!save`).                                                                                                         |
| `!preset`                  | Print the last assembled preset messages sent to the model (before the latest user message).                                                                           |
| `!clear`                   | Clear in-memory conversation history.                                                                                                                                  |
| `!history`                 | Print conversation history (each message truncated to 120 characters).                                                                                                 |

## 4. Configuration

### 4.1. Optional Environment Variables

| Variable     | Required | Description                                                                                           |
| ------------ | -------- | ----------------------------------------------------------------------------------------------------- |
| `UV_PROJECT` | No       | Path passed to `uv run --project` in startup scripts. If unset, scripts use the default project path. |

Optional variables for the `knowledge_graph` MCP server (Neo4j):

| Variable                      | Default                 | Description                             |
| ----------------------------- | ----------------------- | --------------------------------------- |
| `NEO4J_URI`                   | `bolt://localhost:7687` | Neo4j connection URI.                   |
| `NEO4J_USER`                  | `neo4j`                 | Neo4j username.                         |
| `NEO4J_PASSWORD`              | `password`              | Neo4j password.                         |
| `NEO4J_DATABASE`              | `neo4j`                 | Neo4j database name.                    |
| `NEO4J_QUERY_TIMEOUT_SECONDS` | `6`                     | Query timeout in seconds.               |
| `KG_DEFAULT_LIMIT`            | `20`                    | Default result limit for graph queries. |
| `KG_MAX_LIMIT`                | `100`                   | Upper bound for graph query results.    |


### 4.2. Hydra Config Map

Agent configuration is composed from files under `config/`:

| File                         | Purpose                                                    |
| ---------------------------- | ---------------------------------------------------------- |
| `config/config.yaml`         | Top-level defaults composition                             |
| `config/llm/default.yaml`    | LLM model (LiteLLM), endpoint, sampling parameters         |
| `config/work/default.yaml`   | Work mode, network switch, sandbox paths, timeout, tool approval |
| `config/mcp_tools/default.yaml` | MCP tool capability defaults                                   |
| `config/mcp/default.yaml`    | MCP endpoints for tool discovery                           |
| `config/system/default.yaml` | History length, recursion limit, thread                    |
| `config/log/default.yaml`    | Log directory and log level                                |
| `config/chat/default.yaml`   | Conversation persistence (`conversation_dir`)              |
| `config/char/default.yaml`   | Character card, lorebook ids, preset segment toggles/order |
| `config/ekb/default.yaml`    | Vector DB paths, embedding model, chunking, search limits  |

### 4.3. MCP Runtime Model

MCP runtime behavior comes from two sources:

- `mcp/config.yaml`: MCP server process launch settings (`transport`, `host`, `port`, `enabled`)
- `config/mcp/default.yaml`: Agent-side MCP endpoints for tool discovery

Default configured MCP servers:

| Server            | Launch transport (`mcp/config.yaml`) | Launch address | Agent endpoint (`config/mcp/default.yaml`) |
| ----------------- | ------------------------------------ | -------------- | ------------------------------------------ |
| `math`            | `streamable-http`                    | `0.0.0.0:8000` | `http://127.0.0.1:8000/mcp`                |
| `code_lint`       | `streamable-http`                    | `0.0.0.0:8001` | `http://127.0.0.1:8001/mcp`                |
| `knowledge_graph` | `streamable-http`                    | `0.0.0.0:8002` | `http://127.0.0.1:8002/mcp`                |

## 5. Work Mode and Policy Reference

Three independent axes control execution:

| Axis | Config field | Purpose |
| ---- | ------------ | ------- |
| **WorkMode** | `work.work_mode` | Filesystem capability (`ro`, `sw`, `aw`, `pl`) |
| **NetworkPolicy** | `work.network.enabled` | Outbound network on/off (default off) |
| **ToolApprovalPolicy** | `work.tool_approval` | Per-call confirmation behavior |

### 5.1. Work Modes

| Mode | Shell | Tools | Typical use |
| ---- | ----- | ----- | ----------- |
| **RO** | read-only sandbox | read tools | Explore code |
| **SW** | read-only sandbox | read + write tools | Safe editing via structured tools |
| **AW** | read-write sandbox | read + write tools | Full shell writes |
| **PL** | read-only sandbox | read + plan write tools | Write plans under `.agent/plans/` |

CLI: `!mode ro|sw|aw|pl`

### 5.2. Network Switch

`work.network.enabled` is independent from work mode. When `false`, shell and MCP tools tagged `needs_network` are blocked.

CLI: `!network on|off`

### 5.3. Tool Approval Policy

Configure approval behavior with `work.tool_approval`:

| Policy | Config | When to use it |
| ------ | ------ | -------------- |
| **Manual** | `manual` | Confirm every tool call |
| **Blacklist Reject** | `blacklist_reject` | Auto-reject write capabilities, confirm others |
| **Universal Reject** | `universal_reject` | Strict no-tool execution |
| **Whitelist Accept** | `whitelist_accept` | Auto-approve read capabilities, confirm writes |
| **Universal Accept** | `universal_accept` | Fully automatic execution |

MCP tool capabilities are configured in `config/mcp_tools/default.yaml`. Use `tool_defaults` for global MCP tool tags (do not use Hydra's reserved `defaults` key):

```yaml
tool_defaults:
  capability: ro
  needs_network: true

tools:
  some_mcp_tool:
    capability: rw
    needs_network: false
```

This project exposes both local Python tools and MCP-discovered remote tools.

### 6.1. Local Built-In Tools

| Tool name | Capability | Source | Description |
| --------- | ---------- | ------ | ----------- |
| `list_dir`, `read_file`, `grep` | read | `tools/fs_read.py` | Workspace read primitives |
| `write_file`, `apply_patch`, `create_directory` | write | `tools/fs_write.py` | Workspace write primitives |
| `write_plan`, `read_plan`, `list_plans`, `append_plan`, `apply_plan_patch` | plan | `tools/plan.py` | Session plan artifacts |
| `run_shell_readonly` | shell (ro) | `tools/shell.py` | Sandboxed read-only shell |
| `run_shell` | shell (rw) | `tools/shell.py` | Sandboxed read-write shell (AW only) |
| `search_knowledge_base` | read | `tools/embedding_knowledge_base.py` | Search the EKB vector database |

### 6.2. MCP-Discovered Tools

MCP tools are loaded dynamically from endpoints defined in `config/mcp/default.yaml`. Available tool sets depend on enabled servers in `mcp/config.yaml` (for example `math`, `code_lint`, `knowledge_graph`).

### 6.3. Add a New Local Tool

1. Implement the tool under `tools/`.
2. Tag it with `ToolCapability` metadata.
3. Register it in `tools._build_local_tools()`.

No change in `main.py` is required for local tool registration.

## 7. Further Documentation

- EKB usage and commands: [doc/embedding_knowledge_base.md](doc/embedding_knowledge_base.md)
- Prompt manager (pipeline, types, build vs runtime): [doc/prompt_manager.md](doc/prompt_manager.md)
