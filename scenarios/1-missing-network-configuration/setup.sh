#!/usr/bin/env bash

set -eou pipefail

# Set up LocalStack using the CLI (emulate using raw docker commands for now)
# _without_ using docker networking. Set up an application container that tries
# to access LocalStack but cannot.

ROOT_DIR=$(dirname $(readlink -f $0))
pushd $ROOT_DIR >/dev/null
trap "popd >/dev/null" EXIT

# setup common variables
source vars.sh

# build the application container
docker build -t $APPLICATION_IMAGE_NAME .

# start localstack
docker rm -f $LOCALSTACK_CONTAINER_NAME 2>/dev/null || true
# NOTE: publishing the port is required for the CDK deployment :(
docker run --rm -it -d --name $LOCALSTACK_CONTAINER_NAME -v /var/run/docker.sock:/var/run/docker.sock -p 4566:4566 localstack/localstack
# wait for ls to be up
echo "Waiting for LocalStack to be ready" >&2
while true; do
    curl -s http://127.0.0.1:4566/_localstack/health >/dev/null && break
    sleep 1
done

# set up infrastructure
(cd cdk && \
    cdklocal bootstrap && \
    cdklocal deploy --require-approval never)
URL=$(aws --endpoint-url http://localhost:4566 cloudformation describe-stacks --stack-name CdkStack --query Stacks[0].Outputs --output text | grep execute-api | awk '{print $2}')

# launch application container with created api gateway URL as environment variable
docker run --rm -it -d -e UPSTREAM_URL="$URL" --name $APPLICATION_CONTAINER_NAME  -p 5000:5000 $APPLICATION_IMAGE_NAME

echo "Test setup finished"

