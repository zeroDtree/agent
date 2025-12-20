#!/bin/env bash

set -e

max_line_length=120

autoflake --in-place --remove-all-unused-imports --remove-unused-variables -r .
isort .
black --line-length $max_line_length .
