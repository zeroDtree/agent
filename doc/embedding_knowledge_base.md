## Embedding Knowledge Base (EKB)

Indexes local documents into a vector database for semantic retrieval by the agent. Managed via `manage_kb.py`, independently of the agent process.

### Usage

```bash
uv run python manage_kb.py <command> [options]
uv run python manage_kb.py <command> --help
```

| Command  | Description                          |
| -------- | ------------------------------------ |
| `update` | Create or update a knowledge base    |
| `search` | Search a knowledge base              |
| `add`    | Add text content directly            |
| `status` | Show statistics for a knowledge base |
| `list`   | List all knowledge bases             |

### Examples

```bash
# Index current directory into a new knowledge base
uv run python manage_kb.py update -n my_kb -s .

# Index a specific directory
uv run python manage_kb.py update -n blog -s data/blog_content

# Re-index an existing knowledge base
uv run python manage_kb.py update -n blog

# Search
uv run python manage_kb.py search "machine learning concepts" -n blog

# View statistics
uv run python manage_kb.py status -n blog

# List all knowledge bases
uv run python manage_kb.py list

# Add text directly
uv run python manage_kb.py add blog "New content" -t "Title"
```
