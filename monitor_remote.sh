#!/bin/bash

open monitor_docker.html
while true; do
  scp "${1}:${2}/output/html/monitor.html" output/html/
  scp "${1}:${2}/output/image/monitor.png" output/image/
  sleep 0.5
done