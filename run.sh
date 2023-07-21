#!/usr/bin/env bash

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "usage: $0 <source container>" >&2
    exit 1
fi

SOURCE_CONTAINER=$1
shift


IMAGE_NAME=simonrw/debug

# build docker container
docker build -t $IMAGE_NAME .

# run docker container
docker run --rm -it -v /var/run/docker.sock:/var/run/docker.sock --network container:$SOURCE_CONTAINER $IMAGE_NAME diagnose $*
