import json
import logging
from typing import cast
from urllib.parse import urlunparse, ParseResult

from docker import DockerClient
from docker.models.networks import Network

import requests

LOG = logging.getLogger(__name__)


def can_connect_to_localstack_health_endpoint(
    domain: str, port: int = 4566, protocol: str = "http"
) -> bool:
    url = urlunparse(
        ParseResult(
            scheme=protocol,
            netloc=f"{domain}:{port}",
            path="/_localstack/health",
            params="",
            query="",
            fragment="",
        )
    )
    try:
        r = requests.get(url)
    except requests.exceptions.ConnectionError:
        return False

    return r.status_code < 400


def can_connect_to_localstack_health_endpoint_from_container(
    client: DockerClient,
    target_network: Network,
    domain: str,
    port: int = 4566,
    protocol: str = "http",
) -> bool:
    """
    Run this container again, running the "test" mode, which directly tests
    HTTP connectivity.
    """
    # TODO: get image name properly
    LOG.debug("launching docker container to test network connectivity")
    stdout = cast(
        bytes,
        client.containers.run(
            "simonrw/debug:latest",
            ["test", "-t", domain, "--localstack"],
            network=target_network.name,
        ),
    )
    result = json.loads(stdout.decode("utf8"))
    return result.get("connectivity", False)
