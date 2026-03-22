- [1. Core Feature](#1-core-feature)
- [2. Quick Start](#2-quick-start)
  - [2.1. Run agent in host](#21-run-agent-in-host)
  - [2.2. Run agent in docker container](#22-run-agent-in-docker-container)
- [3. Auto Mode](#3-auto-mode)
  - [3.1. Examples](#31-examples)
- [4. Tools](#4-tools)
- [5. Embedding Knowledge Base (EKB)](#5-embedding-knowledge-base-ekb)
  - [5.1. Features](#51-features)
  - [5.2. Usage](#52-usage)
  - [5.3. Examples](#53-examples)
    - [5.3.1. Create Knowledge Base](#531-create-knowledge-base)
    - [5.3.2. Search and Manage](#532-search-and-manage)

## 1. Core Feature

- **AI Agent**: Built on LangGraph with in-memory conversation history and streaming output
- **5-Level Auto Mode**: Configurable tool-call approval policy from fully manual to fully automatic
- **MCP Tool Integration**: Loads tools from multiple MCP servers at startup; unavailable servers are skipped gracefully
- **Shell Execution**: Runs shell commands via subprocess with configurable timeout and working directory
- **Todo List**: In-process todo list tool for task tracking across turns
- **Embedding Knowledge Base (EKB)**: Vector database for document retrieval, managed via `manage_kb.py`
- **Hydra Configuration**: Hierarchical YAML config with command-line override support
- **Docker Support**: Containerized deployment via provided Dockerfile and scripts

## 2. Quick Start

Requires [uv](https://github.com/astral-sh/uv).

### 2.1. Run agent in host

```bash
bash shell_scripts/start.sh
```

This script starts the configured MCP servers, waits until their ports are ready, then launches the agent. MCP servers are stopped automatically on exit.

### 2.2. Run agent in docker container

```bash
bash shell_scripts/build_docker.sh
bash shell_scripts/start.docker.sh
```

## 3. Auto Mode

Controls how tool calls are handled. Configured via `work.auto_mode`.

| Mode                 | Config             | Behavior                                                         |
| -------------------- | ------------------ | ---------------------------------------------------------------- |
| **Manual**           | `manual`           | Every tool call requires user confirmation                       |
| **Blacklist Reject** | `blacklist_reject` | Auto-reject dangerous commands; ask for confirmation on others   |
| **Universal Reject** | `universal_reject` | Auto-reject all tool calls                                       |
| **Whitelist Accept** | `whitelist_accept` | Auto-approve safe tools/commands; ask for confirmation on others |
| **Universal Accept** | `universal_accept` | Auto-approve all tool calls (use only in trusted environments)   |

Safe and dangerous tools / shell commands are defined in `config/tool/default.yaml`.

### 3.1. Examples

```bash
bash shell_scripts/start.docker.sh \
  ++work.auto_mode=universal_accept \
  ++work.working_directory=/tmp/work_dir
```

## 4. Tools

Local tools loaded at startup:

| Tool Name                 | Description                            |
| ------------------------- | -------------------------------------- |
| `run_shell_command_popen` | Execute a shell command, return output |
| `todo_list`               | Manage a per-session todo list         |
| `search_knowledge_base`   | Search an EKB vector database          |

MCP tools are loaded dynamically from the servers listed in `config/mcp/default.yaml`.

To add a new local tool, implement it under `tools/` and register it in `tools/get_all_tools()`. `main.py` does not need to change.

## 5. Embedding Knowledge Base (EKB)

Indexes documents into a vector database for semantic retrieval by the agent.

### 5.1. Features

- Gitignore-aware file filtering with configurable include/exclude regex patterns
- Supports multiple knowledge bases, each stored independently
- Managed separately from the agent via `manage_kb.py`

### 5.2. Usage

```bash
python manage_kb.py <command> [options]
```

| Command  | Description                          |
| -------- | ------------------------------------ |
| `update` | Create or update a knowledge base    |
| `search` | Search a knowledge base              |
| `add`    | Add text content directly            |
| `status` | Show statistics for a knowledge base |
| `list`   | List all knowledge bases             |

Run `python manage_kb.py <command> --help` for full options.

### 5.3. Examples

#### 5.3.1. Create Knowledge Base

```bash
# Index current directory
python manage_kb.py update -n my_kb -s .

# Index a specific directory
python manage_kb.py update -n blog -s data/blog_content

# Re-index (update) an existing knowledge base
python manage_kb.py update -n blog
```

#### 5.3.2. Search and Manage

```bash
# Search
python manage_kb.py search -n blog "machine learning concepts"

# View statistics
python manage_kb.py status -n blog

# List all knowledge bases
python manage_kb.py list

# Add text directly
python manage_kb.py add blog "New content" -t "Title"
```
