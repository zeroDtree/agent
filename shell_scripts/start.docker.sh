SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

mkdir -p "$PROJECT_DIR/work_dir"
mkdir -p "$PROJECT_DIR/docker_agent_uv_venv"

docker run \
	--rm \
	-it \
	-v "$PROJECT_DIR":/tmp/proj_dir \
	-v "$PROJECT_DIR/work_dir":/tmp/work_dir \
	-v "$PROJECT_DIR/docker_agent_uv_venv":/tmp/agent \
	-v ~/.cache:/home/ubuntu/.cache \
	--user 1000:1000 \
	--name agent \
	-e HOME=/home/ubuntu \
	-e UV_PROJECT=/tmp/proj_dir \
	-e UV_PROJECT_ENVIRONMENT=/tmp/agent/.venv \
	-e LLM_API_KEY="$LLM_API_KEY" \
	-e LLM_API_BASE="$LLM_API_BASE" \
	agent:1.0 \
	bash -c 'set -euo pipefail
mkdir -p /tmp/agent
cd /tmp/proj_dir && uv sync
exec bash /tmp/proj_dir/shell_scripts/start.sh "$@"' \
	_ "$@"
