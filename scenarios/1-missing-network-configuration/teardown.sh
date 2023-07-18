#!/usr/bin/env bash

set -eou pipefail

ROOT_DIR=$(dirname $(readlink -f $0))
pushd $ROOT_DIR >/dev/null
trap "popd >/dev/null" EXIT

source vars.sh

docker rm -f $LOCALSTACK_CONTAINER_NAME 2>/dev/null >&2 || true
docker rm -f $APPLICATION_CONTAINER_NAME 2>/dev/null >&2 || true
