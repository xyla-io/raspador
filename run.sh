#!/bin/bash
SCRIPT_DIR=$( cd "$( dirname "$0" )" && pwd )
source "${SCRIPT_DIR}/.venv/bin/activate"
python "${SCRIPT_DIR}/run.py" "$@"
