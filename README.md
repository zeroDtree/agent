
- [1. Quick Start](#1-quick-start)
  - [1.1. Run agent in host](#11-run-agent-in-host)
  - [1.2. Run agent in docker container](#12-run-agent-in-docker-container)
- [2. Auto Mode](#2-auto-mode)
  - [2.1. Examples](#21-examples)
- [3. Tools:](#3-tools)
- [4. Embedding Knowledge Base (EKB)](#4-embedding-knowledge-base-ekb)
  - [4.1. Features](#41-features)
  - [4.2. Usage](#42-usage)
  - [4.3. Examples](#43-examples)
    - [4.3.1. Create Knowledge Base](#431-create-knowledge-base)
    - [4.3.2. Search and Manage](#432-search-and-manage)

## 1. Quick Start

### 1.1. Run agent in host

```bash
conda create -n agent python=3.12
conda activate agent
pip install -r requirements.txt
pip install -r requirements_kb.txt
```

```bash
python main.py
```

### 1.2. Run agent in docker container

```bash
bash shell_scripts/build_docker.sh
bash shell_scripts/start.docker.sh
```

## 2. Auto Mode

Intelligent command processing with 5 security levels - from manual approval to full automation.

| Mode                    | Config             | Behavior                              | Use Case                  |
| ----------------------- | ------------------ | ------------------------------------- | ------------------------- |
| 🤚 **Manual**           | `manual`           | All commands need confirmation        | Production, learning      |
| 🚫 **Blacklist Reject** | `blacklist_reject` | Auto-reject dangerous, confirm others | Development               |
| ⛔ **Universal Reject** | `universal_reject` | Auto-reject all commands              | Read-only scenarios       |
| ✅ **Whitelist Accept** | `whitelist_accept` | Auto-approve safe, reject dangerous   | Balanced automation       |
| 🟢 **Universal Accept** | `universal_accept` | Auto-approve everything ⚠️            | Trusted environments only |

### 2.1. Examples

```bash
bash shell_scripts/start.docker.sh \
  ++work.auto_mode=universal_accept \
  ++work.working_directory=/tmp/work_dir
```

## 3. Tools:

| Tool Name                 | Description               |
| ------------------------- | ------------------------- |
| `search_knowledge_base`   | Search the knowledge base |
| `run_shell_command_popen` | Run a shell command       |

## 4. Embedding Knowledge Base (EKB)

Convert various document types to vector database for AI retrieval.

### 4.1. Features

- **Smart Filtering**: Automatic .gitignore support and flexible regex patterns
- **Configurable Processing**: Control include/exclude pattern order
- **Multiple Formats**: Support for various document types

### 4.2. Usage

Manage knowledge bases with `python manage_kb.py`:

| Command  | Description                        |
| -------- | ---------------------------------- |
| `update` | Create or update knowledge base    |
| `search` | Search knowledge base              |
| `add`    | Add text content to knowledge base |
| `status` | Show statistics                    |
| `list`   | List all knowledge bases           |

Use `python manage_kb.py <command> --help` for detailed options.

### 4.3. Examples

#### 4.3.1. Create Knowledge Base

```bash
# From current directory
python manage_kb.py update -n my_kb -s .

# From specific directory
python manage_kb.py update -n blog -s data/blog_content

# Update existing knowledge base
python manage_kb.py update -n blog
```

#### 4.3.2. Search and Manage

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
