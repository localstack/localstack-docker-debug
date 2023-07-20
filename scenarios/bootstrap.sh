#!/usr/bin/env bash

# one time setup for the scenarios

set -euo pipefail
set -x

ROOT_DIR=$(dirname $(readlink -f $0))
pushd $ROOT_DIR >/dev/null
trap "popd >/dev/null" EXIT

for scenario in 1-missing-network-configuration 2-no-subdomain-support 3-urls-with-localhost; do
    (cd $scenario/cdk && npm install)
done


