- [1. Core Features](#1-core-features)
- [2. Quick Start](#2-quick-start)
  - [2.1. Clone the repository](#21-clone-the-repository)
  - [2.2. Run in host](#22-run-in-host)
  - [2.3. Run in Docker](#23-run-in-docker)
- [3. Configuration](#3-configuration)
- [4. Auto Mode](#4-auto-mode)
- [5. Tools](#5-tools)
- [6. Embedding Knowledge Base (EKB)](#6-embedding-knowledge-base-ekb)
  - [6.1. Usage](#61-usage)
  - [6.2. Examples](#62-examples)

---

## 1. Core Features

- **LangGraph Agent**: Stateful conversation graph with in-memory history and streaming output
- **5-Level Auto Mode**: Configurable tool-call approval policy, from fully manual to fully automatic
- **MCP Integration**: Loads tools from multiple MCP servers at startup; unavailable servers are skipped
- **Shell Execution**: Runs shell commands via subprocess with configurable timeout and working directory
- **Todo List**: In-process todo list tool for multi-turn task tracking
- **Embedding Knowledge Base (EKB)**: Vector database for semantic document retrieval
- **Hydra Configuration**: Hierarchical YAML config with command-line override support
- **Docker Support**: Containerized deployment via provided Dockerfile and helper scripts

## 2. Quick Start

Requires [uv](https://github.com/astral-sh/uv).

### 2.1. Clone the repository

```bash
git clone git@github.com:zeroDtree/agent.git
cd agent
git submodule update --init --recursive
```

The `mcp` submodule contains the MCP server implementations (`math`, `code_lint`).

### 2.2. Run in host

```bash
bash shell_scripts/start.sh [hydra overrides...]
```

This starts the MCP servers defined in `mcp/config.yaml`, waits until their ports are ready, then launches the agent. MCP servers are stopped automatically on exit.

### 2.3. Run in Docker

```bash
bash shell_scripts/build_docker.sh
bash shell_scripts/start.docker.sh [hydra overrides...]
```

The container mounts the project at `/tmp/proj_dir` and a writable work directory at `/tmp/work_dir`.

## 3. Configuration

Config files live under `config/` and are composed by Hydra at startup:

| File                         | What it controls                         |
| ---------------------------- | ---------------------------------------- |
| `config/config.yaml`         | Top-level defaults composition           |
| `config/llm/deepseek.yaml`   | LLM endpoint, model, and sampling params |
| `config/work/default.yaml`   | Working directory, timeout, auto mode    |
| `config/tool/default.yaml`   | Safe / dangerous tool and command lists  |
| `config/mcp/default.yaml`    | MCP server URLs                          |
| `config/system/default.yaml` | History length, recursion limit, thread  |
| `config/log/default.yaml`    | Log directory and level                  |

Any value can be overridden on the command line using Hydra syntax:

```bash
bash shell_scripts/start.sh \
  ++work.auto_mode=whitelist_accept \
  ++work.working_directory=/tmp/work_dir
```

## 4. Auto Mode

Controls how tool calls are routed. Set via `work.auto_mode`.

| Mode                 | Config             | Behavior                                                         |
| -------------------- | ------------------ | ---------------------------------------------------------------- |
| **Manual**           | `manual`           | Every tool call requires user confirmation                       |
| **Blacklist Reject** | `blacklist_reject` | Auto-reject dangerous commands; ask for confirmation on others   |
| **Universal Reject** | `universal_reject` | Auto-reject all tool calls                                       |
| **Whitelist Accept** | `whitelist_accept` | Auto-approve safe tools/commands; ask for confirmation on others |
| **Universal Accept** | `universal_accept` | Auto-approve all tool calls                                      |

Safe and dangerous tool/command lists are defined in `config/tool/default.yaml`.

## 5. Tools

Local tools loaded at startup via `tools.get_all_tools()`:

| Tool                      | Description                            |
| ------------------------- | -------------------------------------- |
| `run_shell_command_popen` | Execute a shell command, return output |
| `todo_list`               | Manage a per-session todo list         |
| `search_knowledge_base`   | Search an EKB vector database          |

MCP tools (`math`, `code_lint`, and others) are loaded dynamically from the servers listed in `config/mcp/default.yaml`.

To add a new local tool: implement it under `tools/`, register it in `tools.get_all_tools()`. `main.py` does not need to change.

## 6. Embedding Knowledge Base (EKB)

Indexes local documents into a vector database for semantic retrieval by the agent. Managed via `manage_kb.py`, independently of the agent process.

### 6.1. Usage

```bash
python manage_kb.py <command> [options]
python manage_kb.py <command> --help
```

| Command  | Description                          |
| -------- | ------------------------------------ |
| `update` | Create or update a knowledge base    |
| `search` | Search a knowledge base              |
| `add`    | Add text content directly            |
| `status` | Show statistics for a knowledge base |
| `list`   | List all knowledge bases             |

### 6.2. Examples

```bash
# Index current directory into a new knowledge base
python manage_kb.py update -n my_kb -s .

# Index a specific directory
python manage_kb.py update -n blog -s data/blog_content

# Re-index an existing knowledge base
python manage_kb.py update -n blog

# Search
python manage_kb.py search -n blog "machine learning concepts"

# View statistics
python manage_kb.py status -n blog

# List all knowledge bases
python manage_kb.py list

# Add text directly
python manage_kb.py add blog "New content" -t "Title"
```
