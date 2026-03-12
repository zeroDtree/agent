- [1. Core Features](#1-core-features)
- [2. Quick Start](#2-quick-start)
  - [2.1. Run agent in host](#21-run-agent-in-host)
  - [2.2. Run agent in docker container](#22-run-agent-in-docker-container)
- [3. Auto Mode](#3-auto-mode)
  - [3.1. Examples](#31-examples)
- [4. Tools:](#4-tools)
- [5. Embedding Knowledge Base (EKB)](#5-embedding-knowledge-base-ekb)
  - [5.1. Features](#51-features)
  - [5.2. Usage](#52-usage)
  - [5.3. Examples](#53-examples)
    - [5.3.1. Create Knowledge Base](#531-create-knowledge-base)
    - [5.3.2. Search and Manage](#532-search-and-manage)

## 1. Core Features

- **🤖 Intelligent AI Agent**: Built on LangGraph framework with state management and memory support
- **🔒 5-Level Security System**: Flexible auto-mode with manual, blacklist, whitelist, universal reject/accept modes
- **📚 Embedding Knowledge Base (EKB)**: Vector database system for document retrieval with smart filtering
- **🔧 MCP Tool Integration**: Support for Model Context Protocol (MCP) tools for extended functionality
- **💻 Shell Command Execution**: Safe shell command execution with timeout and working directory control
- **⚙️ Flexible Configuration**: Hydra-based configuration management with hierarchical config files
- **🐳 Docker Support**: Secure containerized deployment with isolated environment for safe command execution

## 2. Quick Start

### 2.1. Run agent in host

```bash
conda create -n agent python=3.12
conda activate agent
pip install -U -r requirements.txt
pip install -U -r requirements_kb.txt
```

```bash
python main.py
```

### 2.2. Run agent in docker container

```bash
bash shell_scripts/build_docker.sh
bash shell_scripts/start.docker.sh
```

## 3. Auto Mode

Intelligent command processing with 5 security levels - from manual approval to full automation.

| Mode                    | Config             | Behavior                              | Use Case                  |
| ----------------------- | ------------------ | ------------------------------------- | ------------------------- |
| 🤚 **Manual**           | `manual`           | All commands need confirmation        | Production, learning      |
| 🚫 **Blacklist Reject** | `blacklist_reject` | Auto-reject dangerous, confirm others | Development               |
| ⛔ **Universal Reject** | `universal_reject` | Auto-reject all commands              | Read-only scenarios       |
| ✅ **Whitelist Accept** | `whitelist_accept` | Auto-approve safe, reject dangerous   | Balanced automation       |
| 🟢 **Universal Accept** | `universal_accept` | Auto-approve everything ⚠️            | Trusted environments only |

### 3.1. Examples

```bash
bash shell_scripts/start.docker.sh \
  ++work.auto_mode=universal_accept \
  ++work.working_directory=/tmp/work_dir
```

## 4. Tools:

| Tool Name                 | Description               |
| ------------------------- | ------------------------- |
| `search_knowledge_base`   | Search the knowledge base |
| `run_shell_command_popen` | Run a shell command       |

## 5. Embedding Knowledge Base (EKB)

Convert various document types to vector database for AI retrieval.

### 5.1. Features

- **Smart Filtering**: Automatic .gitignore support and flexible regex patterns
- **Configurable Processing**: Control include/exclude pattern order
- **Multiple Formats**: Support for various document types

### 5.2. Usage

Manage knowledge bases with `python manage_kb.py`:

| Command  | Description                        |
| -------- | ---------------------------------- |
| `update` | Create or update knowledge base    |
| `search` | Search knowledge base              |
| `add`    | Add text content to knowledge base |
| `status` | Show statistics                    |
| `list`   | List all knowledge bases           |

Use `python manage_kb.py <command> --help` for detailed options.

### 5.3. Examples

#### 5.3.1. Create Knowledge Base

```bash
# From current directory
python manage_kb.py update -n my_kb -s .

# From specific directory
python manage_kb.py update -n blog -s data/blog_content

# Update existing knowledge base
python manage_kb.py update -n blog
```

#### 5.3.2. Search and Manage

```bash
# Search knowledge base
python manage_kb.py search -n blog "machine learning concepts"

# View statistics
python manage_kb.py status -n blog

# List all knowledge bases
python manage_kb.py list

# Add text directly
python manage_kb.py add blog "New content" -t "Title"
```
