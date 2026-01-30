#!/usr/bin/env bash

set -eou pipefail

# Set up LocalStack using the CLI (emulate using raw docker commands for now)
# _without_ using docker networking. Set up an application container that tries
# to access LocalStack but cannot.

if test -z ${LOCALSTACK_AUTH_TOKEN:-}; then
    echo "Error: must set LOCALSTACK_AUTH_TOKEN" >&2
    exit 1
fi

ROOT_DIR=$(dirname $(readlink -f $0))
pushd $ROOT_DIR >/dev/null
trap "popd >/dev/null" EXIT

# setup common variables
source vars.sh

docker compose up -d localstack

echo "Waiting for LocalStack to be ready" >&2
while true; do
    curl -s http://127.0.0.1:4566/_localstack/health >/dev/null && break
    sleep 1
done

# set up infrastructure
(cd cdk && \
    cdklocal bootstrap && \
    cdklocal deploy --require-approval never)
