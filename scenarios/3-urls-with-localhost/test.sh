#!/usr/bin/env bash

set -euo pipefail
set -x

ROOT_DIR=$(dirname $(readlink -f $0))
pushd $ROOT_DIR >/dev/null
trap "popd >/dev/null" EXIT

docker compose run --build application
