#!/bin/bash
# Manage MCP servers defined in mcp/config.yaml.
# Usage:
#   ./start_mcp.sh [--wait]   start servers; --wait blocks until ports are ready
#   ./start_mcp.sh stop       gracefully stop all running MCP servers

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
UV_PROJECT="${UV_PROJECT:-$PROJECT_DIR}"
MCP_DIR="$PROJECT_DIR/mcp"
LOG_DIR="$PROJECT_DIR/logs/mcp"

mkdir -p "$LOG_DIR"

if ! command -v uv &> /dev/null; then
    echo "Error: uv not found in PATH"
    exit 1
fi

# ---------------------------------------------------------------------------
# Read host/port from mcp/config.yaml with a small inline Python snippet
# ---------------------------------------------------------------------------
get_server_info() {
    local server_name="$1"
    uv run --project "$UV_PROJECT" python - <<EOF
import sys
sys.path.insert(0, "$MCP_DIR")
from config_loader import load_server_config
cfg = load_server_config("$server_name", "$MCP_DIR/config.yaml")
transport = cfg.get("transport", "stdio")
host = cfg.get("host", "127.0.0.1")
port = cfg.get("port", 0)
print(f"{transport}:{host}:{port}")
EOF
}

# ---------------------------------------------------------------------------
# Stop a single server by its saved pid file
# ---------------------------------------------------------------------------
stop_server() {
    local name="$1"
    local pid_file="$LOG_DIR/${name}.pid"

    if [ ! -f "$pid_file" ]; then
        echo "[$name] No pid file found, skipping"
        return 0
    fi

    local pid
    pid=$(cat "$pid_file")

    if kill -0 "$pid" 2>/dev/null; then
        echo "[$name] Stopping pid $pid"
        kill "$pid" 2>/dev/null
        # Wait up to 5 s for the process to exit
        local waited=0
        while kill -0 "$pid" 2>/dev/null; do
            sleep 0.2
            waited=$((waited + 1))
            if [ "$waited" -ge 25 ]; then
                echo "[$name] Process $pid did not exit cleanly, sending SIGKILL"
                kill -9 "$pid" 2>/dev/null
                break
            fi
        done
        echo "[$name] Stopped"
    else
        echo "[$name] Process $pid is not running"
    fi

    rm -f "$pid_file"
}

# ---------------------------------------------------------------------------
# Stop all servers (called on exit or via ./start_mcp.sh stop)
# ---------------------------------------------------------------------------
stop_all() {
    echo "Stopping MCP servers..."
    stop_server "math"
    stop_server "code_lint"
    stop_server "knowledge_graph"
}

# Handle "stop" sub-command
if [ "${1:-}" = "stop" ]; then
    stop_all
    exit 0
fi

# ---------------------------------------------------------------------------
# Start a single server
# ---------------------------------------------------------------------------
start_server() {
    local name="$1"
    local module="$2"

    local info
    info=$(get_server_info "$name")
    local transport host port
    transport=$(echo "$info" | cut -d: -f1)
    host=$(echo "$info"     | cut -d: -f2)
    port=$(echo "$info"     | cut -d: -f3)

    if [ "$transport" = "stdio" ]; then
        echo "[$name] transport=stdio — skipping (stdio servers are launched on demand)"
        return 0
    fi

    local log_file="$LOG_DIR/${name}.log"

    # Kill any existing process on the same port
    local old_pid
    old_pid=$(lsof -ti tcp:"$port" 2>/dev/null)
    if [ -n "$old_pid" ]; then
        echo "[$name] Stopping stale process on port $port (pid $old_pid)"
        kill "$old_pid" 2>/dev/null
        sleep 0.5
    fi

    echo "[$name] Starting on $host:$port (log: $log_file)"
    uv run --project "$UV_PROJECT" python "$MCP_DIR/$module" \
        > "$log_file" 2>&1 &
    echo $! > "$LOG_DIR/${name}.pid"
    echo "[$name] pid $!"
}

# ---------------------------------------------------------------------------
# Wait until a TCP port accepts connections
# ---------------------------------------------------------------------------
wait_for_port() {
    local name="$1"
    local port="$2"
    local max_wait="${3:-15}"
    local elapsed=0

    while ! nc -z 127.0.0.1 "$port" 2>/dev/null; do
        sleep 0.5
        elapsed=$((elapsed + 1))
        if [ "$elapsed" -ge "$((max_wait * 2))" ]; then
            echo "[$name] ERROR: port $port not ready after ${max_wait}s"
            return 1
        fi
    done
    echo "[$name] port $port ready (${elapsed}x0.5s)"
}

# ---------------------------------------------------------------------------
# Start servers
# ---------------------------------------------------------------------------
start_server "math"      "calculate.py"
start_server "code_lint" "code_lint.py"
start_server "knowledge_graph" "knowledge_graph.py"

# ---------------------------------------------------------------------------
# Optionally wait for all HTTP servers to be healthy
# ---------------------------------------------------------------------------
if [ "${1:-}" = "--wait" ]; then
    echo "Waiting for MCP servers to be ready..."
    for entry in math:8000 code_lint:8001 knowledge_graph:8002; do
        name="${entry%%:*}"
        port="${entry##*:}"

        # Re-check transport; only wait for non-stdio servers
        info=$(get_server_info "$name")
        transport=$(echo "$info" | cut -d: -f1)
        if [ "$transport" != "stdio" ]; then
            wait_for_port "$name" "$port" 15 || { stop_all; exit 1; }
        fi
    done
    echo "All MCP servers are ready."
fi
