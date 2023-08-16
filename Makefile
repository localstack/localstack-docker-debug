IMAGE_NAME ?= ghcr.io/localstack/localstack-docker-debug:main

help:                   ## Show this help
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/:.*##\s*/##/g' | awk -F'##' '{ printf "%-25s %s\n", $$1, $$2 }'

docker-build: 			## Build the docker image
	docker build -t ${IMAGE_NAME} .

