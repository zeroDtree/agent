docker run \
	--rm \
	-it \
	-v .:/tmp/proj_dir \
	-v ./work_dir:/tmp/work_dir \
	-v ~/.cache:/home/ubuntu/.cache \
	--gpus all \
	--user 1000:1000 --name agent \
	-e HOME=/home/ubuntu \
	-e DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY \
	agent:1.0 \
	bash -lc "source /opt/conda/etc/profile.d/conda.sh && conda activate agent && python /tmp/proj_dir/main.py $*"
