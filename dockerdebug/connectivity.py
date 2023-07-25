from enum import Enum
import json
import logging
import socket
from typing import cast
from urllib.parse import urlunparse, ParseResult

from docker import DockerClient
from docker.models.networks import Network

import requests

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


class CannotConnectReason(Enum):
    can_connect = "can-connect"
    dns = "dns"
    bad_status_code = "bad-status-code"
    unknown = "unknown"


class CustomEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, CannotConnectReason):
            return o.value
        return super().default(o)


def can_connect_to_localstack_health_endpoint(
    domain: str, port: int = 4566, protocol: str = "http", timeout: int = 3
) -> CannotConnectReason:
    # test dns first
    LOG.debug("testing DNS")
    try:
        socket.gethostbyname_ex(domain)
    except Exception as e:
        return CannotConnectReason.dns

    # now test making an HTTP request
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
    LOG.debug(f"making request to {url}")
    try:
        LOG.debug("making request")
        r = requests.get(url, timeout=timeout)
    except requests.exceptions.ConnectionError as e:
        LOG.debug(f"cannot connect to health endpoint: {e}")
        if "NameResolutionError" in str(e):
            return CannotConnectReason.dns

        return CannotConnectReason.unknown

    LOG.debug(f"got response from health endpoint status {r.status_code}")
    if r.status_code >= 400:
        return CannotConnectReason.bad_status_code

    return CannotConnectReason.can_connect


def can_connect_to_localstack_health_endpoint_from_container(
    client: DockerClient,
    target_network: Network,
    domain: str,
    port: int = 4566,
    protocol: str = "http",
) -> CannotConnectReason:
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
    # parse back into CannotConnectReason
    return CannotConnectReason(result.get("connectivity", "unknown"))
