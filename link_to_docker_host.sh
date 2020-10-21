#!/bin/bash

for LINKPATH in raspador output configurations bots
do
  echo "Symbolically linking ${LINKPATH} to docker /dockerhost/app/${LINKPATH}"
  rm -rf "${LINKPATH}"
  ln -s "/dockerhost/app/${LINKPATH}" "${LINKPATH}"
done
