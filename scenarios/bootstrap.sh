#!/usr/bin/env bash

# one time setup for the scenarios

set -euo pipefail
set -x

for scenario in 1-missing-network-configuration 2-no-subdomain-support 3-urls-with-localhost; do
    (cd $scenario/cdk && npm install)
done


