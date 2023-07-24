#!/usr/bin/env bash

set -euo pipefail

IMAGE_NAME=simonrw/debug

# build docker container
docker build -t $IMAGE_NAME . >&2

# run docker container
docker run --rm -it -v /var/run/docker.sock:/var/run/docker.sock $IMAGE_NAME probe $*
