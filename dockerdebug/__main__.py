from __future__ import annotations
from dataclasses import dataclass
import json
import logging
import socket
import sys
from typing import Iterable, Type, cast, Self, Any, TypedDict, TypeVar, Generator
from urllib.parse import urlunparse, ParseResult

import click
from click.exceptions import ClickException
from docker import DockerClient
from docker.errors import NotFound
from docker.models.containers import Container
from docker.models.networks import Network

import requests

from dockerdebug.probe import Prober

logging.basicConfig(level=logging.WARNING, format="%(asctime)s | %(levelname)-8s | %(message)s")
LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


class CannotFindLocalStackContainer(Exception):
    pass


class MultipleLocalStackContainerCandidates(Exception):
    def __init__(self, candidates: set[Container]):
        self.candidates = candidates


def _containers_with_localstack_labels(containers: Iterable[Container]) -> set[Container]:
    candidates = set()
    for container in containers:
        if container.labels.get("authors") == "LocalStack Contributors":
            candidates.add(container)
            continue
    return candidates


def _containers_with_exposed_ports(containers: Iterable[Container]) -> set[Container]:
    candidates = set()
    for container in containers:
        if "4566/tcp" in container.ports:
            candidates.add(container)
    return candidates


def find_localstack_container(containers: Iterable[Container]) -> Container:
    candidates: set[Container] = set()
    candidates = candidates.union(_containers_with_localstack_labels(containers))
    candidates = candidates.union(_containers_with_exposed_ports(containers))
    if len(candidates) == 1:
        return list(candidates)[0]
    elif len(candidates) == 0:
        raise CannotFindLocalStackContainer()
    else:
        raise MultipleLocalStackContainerCandidates(candidates)


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

    def present_suggestions(self):
        click.echo("# Suggestions to fix your connectivity issue:")

        # rely on Suggestion implementing __gt__
        self.suggestions.sort()
        for i, suggestion in enumerate(sorted(self.suggestions)):
            click.echo(f"{i + 1}. {suggestion}")

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

@click.group
def main():
    pass


@main.command
@click.option(
    "-t",
    "--target-container",
    "target_container_id",
    help="Container to test connectivity to. If not specified, assume LocalStack",
)
@click.option(
    "--localstack",
    "target_is_localstack",
    help="Assume target container is localstack",
    is_flag=True,
)
def diagnose(target_container_id: str | None, target_is_localstack: bool):
    client = DockerClient()
    diagnoser = Diagnoser(client)

    source_container = cast(Container, client.containers.get(socket.gethostname()))

    if target_container_id is not None:
        try:
            target_container = cast(Container, client.containers.get(target_container_id))
        except NotFound:
            raise ClickException(f"could not find container {target_container_id}")
    else:
        containers = cast(list[Container], client.containers.list())
        target_container = find_localstack_container(containers)
        target_is_localstack = True

    LOG.info(f"testing connectivity from {source_container.name} to {target_container.name}")
    if target_is_localstack:
        LOG.info("assuming target container is localstack")
        diagnoser.test_connectivity_to_localstack(client, target_container)

    diagnoser.present_suggestions()


@main.command
def probe():
    """
    Capture all running containers, their network attachments, their network interfaces
    and output to a JSON report.
    """
    client = DockerClient()
    prober = Prober(client)
    report = prober.probe()
    json.dump(report, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
