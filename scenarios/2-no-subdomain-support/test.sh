#!/usr/bin/env bash

set -euo pipefail
set -x


docker compose exec application dig +noall +answer +comments localstack execute-api.localstack

curl http://127.0.0.1:5000
