#!/usr/bin/env bash

set -eou pipefail

ROOT_DIR=$(dirname $(readlink -f $0))
pushd $ROOT_DIR >/dev/null
trap "popd >/dev/null" EXIT

source vars.sh

docker compose down
