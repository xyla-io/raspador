#!/bin/bash

set -e
set -x

source .venv/bin/activate
mkdir -p documentation/sphinx/_static
cd documentation/sphinx
make clean html
