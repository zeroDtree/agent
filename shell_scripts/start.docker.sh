mkdir -p ./work_dir

docker run \
	--rm \
	-it \
	-v .:/tmp/proj_dir \
	-v ./work_dir:/tmp/work_dir \
	-v ~/.cache:/home/ubuntu/.cache \
	--user 1000:1000 \
	--name agent \
	-e HOME=/home/ubuntu \
	-e UV_PROJECT=/tmp/agent \
	-e OPENAI_API_KEY="$OPENAI_API_KEY" \
	-e OPENAI_API_BASE="$OPENAI_API_BASE" \
	agent:1.0 \
	bash /tmp/proj_dir/shell_scripts/start.sh "$@"
