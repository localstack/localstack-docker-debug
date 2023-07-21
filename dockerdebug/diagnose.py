from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Type, Self, Any
from urllib.parse import urlunparse, ParseResult

import click
from docker import DockerClient
from docker.models.containers import Container
import requests

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


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


def get_container_user_network_names(container: Container) -> list[str]:
    assert container.attrs is not None
    settings = container.attrs["NetworkSettings"]
    network_names = []
    for network_name in settings.get("Networks", {}):
        if network_name == "bridge":
            continue

        network_names.append(network_name)

    return network_names


@dataclass
class Suggestion:
    user_facing_text: str
    preference: int

    def __str__(self) -> str:
        return self.user_facing_text

    @classmethod
    def add_user_defined_networks(cls: Type[Self]) -> Self:
        return cls(
            user_facing_text="Your container is not running in a docker user-defined network. Please see the troubleshooting docs: https://docs.localstack.cloud/references/network-troubleshooting/endpoint-url/#from-your-container",
            preference=10,
        )

    def __gt__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            raise TypeError(f"cannot compare types {self.__class__} to {other.__class__}")

        return self.preference > other.preference


class Diagnoser:
    suggestions: list[Suggestion]

    def __init__(self, client: DockerClient):
        self.client = client
        self.suggestions = []

    def test_connectivity_to_localstack(self, client: DockerClient, container: Container):
        LOG.info("testing connectivity to LocalStack")
        # try connecting as is using the container name
        if container.name and can_connect_to_localstack_health_endpoint(container.name):
            LOG.info("connectivity to target container successful")
            return

        LOG.info(f"cannot connect to container via name {container.name}")
        # try to find a way to connect to localstack
        if networks := get_container_user_network_names(container):
            for network in networks:
                breakpoint()
                # attach this container to the network and try
                # detach this container from the network
                pass
        else:
            LOG.info("no user-defined networks found")
            # TODO: test adding both source and target to the same network?
            self.suggestions.append(Suggestion.add_user_defined_networks())

    def present_suggestions(self):
        if not self.suggestions:
            click.echo(
                "Sorry we don't have any suggestions. Please see the troubleshooting docs: https://docs.localstack.cloud/references/network-troubleshooting/endpoint-url/#from-your-container",
                err=True,
            )
            return

        click.echo("# Suggestions to fix your connectivity issue:")

        # rely on Suggestion implementing __gt__
        self.suggestions.sort()
        for i, suggestion in enumerate(sorted(self.suggestions)):
            click.echo(f"{i + 1}. {suggestion}")
