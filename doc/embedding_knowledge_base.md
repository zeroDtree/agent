## Embedding Knowledge Base (EKB)

Indexes local documents into a vector database for semantic retrieval by the agent. Managed via `zdt_agent_kb`, independently of the agent process.

### Usage

```bash
uv run zdt_agent_kb <command> [options]
uv run zdt_agent_kb <command> --help
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
uv run zdt_agent_kb update -n my_kb -s .

# Index a specific directory
uv run zdt_agent_kb update -n blog -s data/blog_content

# Re-index an existing knowledge base
uv run zdt_agent_kb update -n blog

# Search
uv run zdt_agent_kb search "machine learning concepts" -n blog

# View statistics
uv run zdt_agent_kb status -n blog

# List all knowledge bases
uv run zdt_agent_kb list

# Add text directly
uv run zdt_agent_kb add blog "New content" -t "Title"
```
