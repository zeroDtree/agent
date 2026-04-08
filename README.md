# Agent

A LangGraph-based agent runtime with MCP integration, shell tooling, configurable tool approval modes, optional embedding-based retrieval, and a prompt manager (lorebook build/runtime plus preset assembly for the chat loop).

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
  - [4. Configuration](#4-configuration)
    - [4.1. Hydra Config Map](#41-hydra-config-map)
    - [4.2. MCP Runtime Model](#42-mcp-runtime-model)
  - [5. Auto Mode Reference](#5-auto-mode-reference)
  - [6. Tooling Model](#6-tooling-model)
    - [6.1. Local Built-In Tools](#61-local-built-in-tools)
    - [6.2. MCP-Discovered Tools](#62-mcp-discovered-tools)
    - [6.3. Add a New Local Tool](#63-add-a-new-local-tool)
  - [7. Further Documentation](#7-further-documentation)

## 2. What This Project Provides

- **Stateful agent runtime**: Uses LangGraph with in-memory conversation state and streaming output.
- **5-level tool approval policy**: Ranges from fully manual to fully automatic (`work.auto_mode`).
- **MCP tool federation**: Loads tools from configured MCP servers; unavailable servers are skipped.
- **Shell command tool**: Executes commands with configurable timeout and working directory.
- **Embedding Knowledge Base (EKB)**: Supports semantic retrieval over indexed files.
- **Prompt manager** (`prompt_manager/`): Compiles `prompts/lorebooks/*/entries` to `lorebook.json`, runs trigger-based injection at each turn, and merges results with core/character/persona segments (see `doc/prompt_manager.md`).
- **Hydra-based configuration**: Hierarchical YAML composition with command-line overrides.
- **Container support**: Includes Docker scripts for build and startup.

## 3. Quick Start

### 3.1. Environment Variables

Set these variables before starting the agent.

Required for LLM requests:

| Variable          | Required | Description                                                                             |
| ----------------- | -------- | --------------------------------------------------------------------------------------- |
| `OPENAI_API_KEY`  | Yes      | API key used by `config/llm/deepseek.yaml`.                                             |
| `OPENAI_API_BASE` | Yes      | Base URL used by `config/llm/deepseek.yaml` (for example DeepSeek-compatible endpoint). |

Optional runtime variable:

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

Example:

```bash
export OPENAI_API_KEY="your_api_key"
export OPENAI_API_BASE="https://your-provider.example/v1"
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

### 3.6. Common Startup Overrides

Use Hydra override syntax to customize runtime behavior at launch:

```bash
bash shell_scripts/start.sh \
  ++work.auto_mode=whitelist_accept \
  ++work.working_directory=/tmp/work_dir
```

## 4. Configuration

### 4.1. Hydra Config Map

Agent configuration is composed from files under `config/`:

| File                         | Purpose                                                    |
| ---------------------------- | ---------------------------------------------------------- |
| `config/config.yaml`         | Top-level defaults composition                             |
| `config/llm/deepseek.yaml`   | LLM endpoint, model, sampling parameters                   |
| `config/work/default.yaml`   | Working directory, timeout, auto mode                      |
| `config/tool/default.yaml`   | Safe and dangerous tools/commands                          |
| `config/mcp/default.yaml`    | MCP endpoints for tool discovery                           |
| `config/system/default.yaml` | History length, recursion limit, thread                    |
| `config/log/default.yaml`    | Log directory and log level                                |
| `config/chat/default.yaml`   | Conversation persistence (`conversation_dir`)              |
| `config/char/default.yaml`   | Character card, lorebook ids, preset segment toggles/order |
| `config/ekb/default.yaml`    | Vector DB paths, embedding model, chunking, search limits  |

### 4.2. MCP Runtime Model

MCP runtime behavior comes from two sources:

- `mcp/config.yaml`: MCP server process launch settings (`transport`, `host`, `port`, `enabled`)
- `config/mcp/default.yaml`: Agent-side MCP endpoints for tool discovery

Default configured MCP servers:

| Server            | Launch transport (`mcp/config.yaml`) | Launch address | Agent endpoint (`config/mcp/default.yaml`) |
| ----------------- | ------------------------------------ | -------------- | ------------------------------------------ |
| `math`            | `streamable-http`                    | `0.0.0.0:8000` | `http://127.0.0.1:8000/mcp`                |
| `code_lint`       | `streamable-http`                    | `0.0.0.0:8001` | `http://127.0.0.1:8001/mcp`                |
| `knowledge_graph` | `streamable-http`                    | `0.0.0.0:8002` | `http://127.0.0.1:8002/mcp`                |

## 5. Auto Mode Reference

Configure approval behavior with `work.auto_mode`:

| Mode                 | Config             | When to use it                                                |
| -------------------- | ------------------ | ------------------------------------------------------------- |
| **Manual**           | `manual`           | You want confirmation for every tool call                     |
| **Blacklist Reject** | `blacklist_reject` | You want dangerous calls rejected, others confirmed manually  |
| **Universal Reject** | `universal_reject` | You want a strict no-tool execution mode                      |
| **Whitelist Accept** | `whitelist_accept` | You want trusted calls auto-approved, others confirmed        |
| **Universal Accept** | `universal_accept` | You want fully automatic tool execution without confirmations |

Safe and dangerous lists are defined in `config/tool/default.yaml`.

## 6. Tooling Model

This project exposes both local Python tools and MCP-discovered remote tools.

### 6.1. Local Built-In Tools

| Tool name                      | Enabled by default | Source                              | Description                               |
| ------------------------------ | ------------------ | ----------------------------------- | ----------------------------------------- |
| `run_shell_command_popen_tool` | Yes                | `tools/shell.py`                    | Execute shell commands and return output  |
| `search_knowledge_base`        | Yes                | `tools/embedding_knowledge_base.py` | Search the EKB vector database            |
| `todo_list_tool`               | No                 | `tools/todo_list.py`                | Manage todo items in conversation context |

### 6.2. MCP-Discovered Tools

MCP tools are loaded dynamically from endpoints defined in `config/mcp/default.yaml`. Available tool sets depend on enabled servers in `mcp/config.yaml` (for example `math`, `code_lint`, `knowledge_graph`).

### 6.3. Add a New Local Tool

1. Implement the tool under `tools/`.
2. Register it in `tools.get_all_tools()`.

No change in `main.py` is required for local tool registration.

## 7. Further Documentation

- EKB usage and commands: [doc/embedding_knowledge_base.md](doc/embedding_knowledge_base.md)
- Prompt manager (pipeline, types, build vs runtime): [doc/prompt_manager.md](doc/prompt_manager.md)
