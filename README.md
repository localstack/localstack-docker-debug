# LocalStack docker debug image

This repository contains the source code for the LocalStack docker debug application.

## Usage

If you have an issue with your docker networking setup, you can use this docker container to investigate further.
The tool has multiple usage modes.

### Diagnose

In this mode, the tool will replicate attempting to connect from your application container to your target container.


```mermaid
flowchart LR;
    ls[LocalStack]
    app[Application Container]

    app --> ls
```

The general usage of this mode is to run

```bash
docker run --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    ghcr.io/localstack/localstack-docker-debug:main \
        diagnose \
        --source-container "Application Container" \
        --target-container "LocalStack"
```

This attempts to diagnose the connectivity issues between your application container and target container by temporarily adjusting docker user-defined networks.

It will output suggestions on what changes to make to the command line.

If the `--localstack` flag is supplied, or the `--target-container` flag is not supplied, we assume the target container is LocalStack, and verify connectivity by making a request to the [health endpoint](https://docs.localstack.cloud/references/internal-endpoints/#localstack-endpoints).

### Probe

This mode scans your docker network for network specific information about the containers you are currently running, and outputs a JSON log file to stdout.

```bash
docker run --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    ghcr.io/localstack/localstack-docker-debug:main \
        probe > topology.json
```

This command collects:

* networks:
    * id
    * name
    * subnet
    * gateway
    * containers:
        * id
        * name
        * image
        * labels
        * status
        * interfaces:
            * network name
            * gateway
            * ip address

and outputs the results to `topology.json`.

### Bundled networking tools

In addition to the code bundled in this docker image, we also add a few networking tools to the container, so that they can be run to gather more information.
The tools we bundle are listed in the [`Dockerfile`](https://github.com/localstack/localstack-docker-debug/tree/main/Dockerfile#L7-L13).

To use the desired tool, run

```bash
docker run --rm \
    --entrypoint <tool> \
    ghcr.io/localstack/localstack-docker-debug:main \
    <args>
```

for example

```
docker run --rm \
    --entrypoint dig \
    ghcr.io/localstack/localstack-docker-debug:main \
    example.com

; <<>> DiG 9.18.16-1~deb12u1-Debian <<>> example.com
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 47090
;; flags: qr rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1

;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 4096
;; QUESTION SECTION:
;example.com.                   IN      A

;; ANSWER SECTION:
example.com.            78631   IN      A       93.184.216.34

;; Query time: 10 msec
;; SERVER: 192.168.0.2#53(192.168.0.2) (UDP)
;; WHEN: Wed Aug 16 08:34:44 UTC 2023
;; MSG SIZE  rcvd: 56
```


## LocalStack team usage

This tool can be installed as a pip package, and gives access to an additional command: `render`.
This command renders the output of the `probe` command to a graphviz dot files:

```bash
python -m dockerdebug render -f <output.json> > output.dot
dot -Tpng -o output.png output.dot
open output.png
```

If this doesn't work, you can generate the png in the container:

```bash
docker run --rm \
    -v <path to topology.json>:/topology.json \
    ghcr.io/localstack/localstack-docker-debug:main render \
    -f /topology.json > out.dot
docker run --rm \
    -v $PWD:/out \
    --entrypoint dot \
    ghcr.io/localstack/localstack-docker-debug:main \
    -Tpng /out/out.dot -o /out/out.png
```

### Package installation

1. Install `dot` (graphviz)
2. `pip install -e .`

### Scenarios

This repository contains scenarios that help explore how this tool works.
Under the `scenarios` subdirectory, there are a number of samples, each that set up docker containers.
Each sample contains the following scripts:

* `setup.sh`: set up the scenario
* `test.sh`: demonstrate the connectivity issue
* `teardown.sh`: remove resources created by the `setup.sh` script


## Security

We mount the docker socket because we have to be able to run docker commands.
If you have concerns about what this tool does, the source code is available in this repo.

## Contributing

TODO
