#!/usr/bin/env bash

set -euo pipefail

IMAGE_NAME=simonrw/debug

# build docker container
docker build -t $IMAGE_NAME .

# run docker container
docker run --rm -it -v /var/run/docker.sock:/var/run/docker.sock $IMAGE_NAME diagnose $*
