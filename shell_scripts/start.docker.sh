mkdir -p ./work_dir
mkdir -p ./uv_agent

docker run \
	--rm \
	-it \
	-v .:/tmp/proj_dir \
	-v ./work_dir:/tmp/work_dir \
	-v ./uv_agent:/tmp/agent \
	-v ~/.cache:/home/ubuntu/.cache \
	--user 1000:1000 \
	--name agent \
	-e HOME=/home/ubuntu \
	-e UV_PROJECT=/tmp/agent \
	-e OPENAI_API_KEY="$OPENAI_API_KEY" \
	-e OPENAI_API_BASE="$OPENAI_API_BASE" \
	agent:1.0 \
	bash -c 'set -euo pipefail
mkdir -p /tmp/agent
cp /tmp/proj_dir/pyproject.toml /tmp/agent/
if [[ -f /tmp/proj_dir/uv.lock ]]; then cp /tmp/proj_dir/uv.lock /tmp/agent/; fi
cd /tmp/agent && uv sync
exec bash /tmp/proj_dir/shell_scripts/start.sh "$@"' \
	_ "$@"
