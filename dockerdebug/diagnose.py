from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import logging
import socket
from typing import Type, Self, Any, cast, Iterable

import click
from docker import DockerClient
from docker.models.containers import Container
from docker.models.networks import Network

from dockerdebug.connectivity import (
    CannotConnectReason,
    can_connect_to_localstack_health_endpoint,
    can_connect_to_localstack_health_endpoint_from_container,
)

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


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
    def add_application_container_to_network(cls: Type[Self], network: Network) -> Self:
        return cls(
            user_facing_text=f"Your container is not running in the same docker user-defined network as the target. Please re-launch your container in the `{network.name}` network.",
            preference=20,
        )

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


def find_self(client: DockerClient) -> Container:
    """
    Finding this container is not straightforward - we cannot use the hostname
    since we are within the network namespace of a target container. Instead,
    we have to look in other places.

    We assume that there is only one debug container running.
    """
    for container in cast(Iterable[Container], client.containers.list()):
        if container.labels.get("cloud.localstack.dockerdebug.name") == "dockerdebug":
            return container

    raise RuntimeError("could not find a reference to this container")


@contextmanager
def attach_to_network(network: Network, container_id: str | None = None):
    container_id = container_id if container_id is not None else socket.gethostname()
    network.connect(container_id)
    try:
        yield
    finally:
        network.disconnect(container_id)


class Diagnoser:
    suggestions: list[Suggestion]

    def __init__(self, client: DockerClient):
        self.client = client
        self.suggestions = []

    def test_connectivity_to_localstack(
        self, client: DockerClient, source_container: Container, target_container: Container
    ):
        """
        target_container == LocalStack
        """
        # try connecting as is using the container name
        if not target_container.name:
            raise RuntimeError("no container name to test with")

        LOG.info(f"testing connectivity to LocalStack from {source_container.name}")

        match can_connect_to_localstack_health_endpoint(target_container.name):
            case CannotConnectReason.can_connect:
                LOG.info("connectivity to target container successful")
                return
            case CannotConnectReason.bad_status_code:
                LOG.info("could reach localstack but got bad status code")
                return
            case CannotConnectReason.dns:
                LOG.info(f"could not resolve name {target_container.name}")
            case CannotConnectReason.unknown:
                LOG.info("could not connect to localstack health endpoint")

        LOG.info("running additional tests")

        # try to find a way to connect to localstack
        network_names = get_container_user_network_names(source_container)
        LOG.debug(f"found networks {network_names} attached to container {source_container.name}")
        if network_names:
            for network_name in network_names:
                LOG.debug(f"testing connectivity from network: {network_name}")
                network = cast(Network, client.networks.get(network_name))
                if can_connect_to_localstack_health_endpoint_from_container(
                    client,
                    network,
                    target_container.name,
                ):
                    LOG.debug("connectivity test successful")
                    self.suggestions.append(
                        Suggestion.add_application_container_to_network(network)
                    )
                else:
                    LOG.debug("cannot connect")
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
