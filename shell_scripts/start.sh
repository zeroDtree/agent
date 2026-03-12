#!/bin/bash

cd ~/proj/my_agent

# Initialize conda if not already done
if ! command -v conda &> /dev/null; then
    echo "Error: conda not found in PATH"
    exit 1
fi

# Source conda initialization
eval "$(conda shell.bash hook)"

# Activate conda environment
conda activate exp

echo $@

python main.py $@
