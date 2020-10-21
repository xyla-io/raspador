#!/bin/bash

set -e
set -x

install_development_packages () {
  for DEVPKG in $(ls -d */)
  do
    cd $DEVPKG
    if [ -f requirements.txt ]; then
      pip install -r requirements.txt
    fi
    if [ -f setup.py ]; then
      python setup.py develop
    fi
    if [ -d development_packages ]; then
      cd development_packages
      install_development_packages
      cd ..
    fi
    cd ..
  done
}

source local_configure
PYTHONCOMMAND=${PYTHONCOMMAND:-python3}
PLATFORM=${PLATFORM:-osx}

if [ "${PLATFORM}" != 'docker' ]; then
  git submodule update --init
fi

rm -rf .venv
$PYTHONCOMMAND -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

chmod 700 output
chmod 700 output/log
chmod 700 configurations

cd development_packages
install_development_packages
cd ..

if [ "${PLATFORM}" == 'docker' ]; then
  pip install pyvirtualdisplay
  pip install pillow
  pip install pyscreenshot
fi

deactivate
