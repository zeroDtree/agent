#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

bash "$PROJECT_DIR/shell_scripts/start.sh" ++work.working_directory="$PWD" "$@"