- [1. Auto Mode](#1-auto-mode)
- [2. Tools:](#2-tools)
- [3. Embedding Knowledge Base (EKB)](#3-embedding-knowledge-base-ekb)
  - [3.1. Features](#31-features)
  - [3.2. Usage](#32-usage)
  - [3.3. Examples](#33-examples)
    - [3.3.1. Create Knowledge Base](#331-create-knowledge-base)
    - [3.3.2. Search and Manage](#332-search-and-manage)

## 1. Auto Mode

Intelligent command processing with 5 security levels - from manual approval to full automation.

| Mode                    | Config             | Behavior                              | Use Case                  |
| ----------------------- | ------------------ | ------------------------------------- | ------------------------- |
| 🤚 **Manual**           | `manual`           | All commands need confirmation        | Production, learning      |
| 🚫 **Blacklist Reject** | `blacklist_reject` | Auto-reject dangerous, confirm others | Development               |
| ⛔ **Universal Reject** | `universal_reject` | Auto-reject all commands              | Read-only scenarios       |
| ✅ **Whitelist Accept** | `whitelist_accept` | Auto-approve safe, reject dangerous   | Balanced automation       |
| 🟢 **Universal Accept** | `universal_accept` | Auto-approve everything ⚠️            | Trusted environments only |

## 2. Tools:

| Tool Name                 | Description               |
| ------------------------- | ------------------------- |
| `search_knowledge_base`   | Search the knowledge base |
| `run_shell_command_popen` | Run a shell command       |

## 3. Embedding Knowledge Base (EKB)

Convert various document types to vector database for AI retrieval.

### 3.1. Features

- **Smart Filtering**: Automatic .gitignore support and flexible regex patterns
- **Configurable Processing**: Control include/exclude pattern order
- **Multiple Formats**: Support for various document types

### 3.2. Usage

Manage knowledge bases with `python manage_kb.py`:

| Command  | Description                        |
| -------- | ---------------------------------- |
| `update` | Create or update knowledge base    |
| `search` | Search knowledge base              |
| `add`    | Add text content to knowledge base |
| `status` | Show statistics                    |
| `list`   | List all knowledge bases           |

Use `python manage_kb.py <command> --help` for detailed options.

### 3.3. Examples

#### 3.3.1. Create Knowledge Base

```bash
# From current directory
python manage_kb.py update -n my_kb -s .

# From specific directory
python manage_kb.py update -n blog -s data/blog_content

# Update existing knowledge base
python manage_kb.py update -n blog
```

#### 3.3.2. Search and Manage

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
