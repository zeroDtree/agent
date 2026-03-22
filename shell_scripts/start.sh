#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

if ! command -v uv &> /dev/null; then
    echo "Error: uv not found in PATH"
    exit 1
fi

# Stop MCP servers on exit (Ctrl-C, normal exit, or error)
cleanup() {
    echo ""
    bash "$SCRIPT_DIR/start_mcp.sh" stop
}
trap cleanup EXIT

# Start MCP servers first and wait until their ports are ready
if ! bash "$SCRIPT_DIR/start_mcp.sh" --wait; then
    echo "ERROR: MCP servers failed to start, aborting."
    exit 1
fi

echo "Args: $*"
if [ -n "${UV_PROJECT:-}" ]; then
    uv run --project "$UV_PROJECT" python "$PROJECT_DIR/main.py" "$@"
else
    uv run main.py "$@"
fi
