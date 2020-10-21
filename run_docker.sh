#!/bin/bash
cd $( dirname "$0" )
SCRIPT_DIR=$( pwd )
. .venv/bin/activate
python run_docker.py "$@" > output/log/run_docker.log 2>&1
if [[ $? != 0 ]]; then
  echo Raspador failed run at `date` with args: "$@" >> output/log/raspador.log 2>&1
fi
