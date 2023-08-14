from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum, auto
import logging
import socket
import uuid
from typing import Callable, Type, Self, Any, cast, Iterable

from docker import DockerClient
from docker.errors import ContainerError, NotFound
from docker.models.containers import Container
from docker.models.networks import Network

from dockerdebug.constants import DEBUG_IMAGE_NAME

LOG = logging.getLogger(__name__)


class Protocol(Enum):
    http = auto()
    https = auto()

    def __str__(self) -> str:
        match self:
            case Protocol.http:
                return "http"
            case Protocol.https:
                return "https"


def short_uid() -> str:
    return str(uuid.uuid4())[:8]


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
    def add_localstack_as_dns_for_subdomain_support(cls: Type[Self]) -> Self:
        return cls(
            user_facing_text="Your container can access LocalStack, however arbitrary subdomain support is not possible. Consider setting the IP address of the LocalStack container as your DNS server.",
            preference=0,
        )

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


@dataclass
class Cleanup:
    name: str
    impl: Callable[[], None]


class Diagnoser(ABC):
    def __init__(
        self,
        client: DockerClient,
        source_container: Container | str,
        target_container: Container | str,
    ):
        self.client = client

        if isinstance(source_container, str):
            self.source = cast(Container, self.client.containers.get(source_container))
        else:
            self.source = source_container

        if isinstance(target_container, str):
            self.target = cast(Container, self.client.containers.get(target_container))
        else:
            self.target = target_container

        self.suggestion_number = 1
        self.cleanups: list[Cleanup] = []

    def test_connectivity(self):
        try:
            self.perform_connectivity_test()
        except Exception as e:
            LOG.warning(f"error performing connectivity test: {e}")
        finally:
            LOG.debug(f"cleaning up: {self.cleanups}")
            for cleanup in self.cleanups[::-1]:
                LOG.debug(f"Running cleanup: {cleanup.name}")
                try:
                    cleanup.impl()
                except Exception as e:
                    LOG.warning(f"failed to run cleanup: {e}")

    @abstractmethod
    def perform_connectivity_test(self):
        pass

    # common steps
    def test_dns(self, test_container_network_name: str | None = None) -> bool:
        try:
            self.client.containers.run(
                image=DEBUG_IMAGE_NAME,
                entrypoint="python",
                command=[
                    "-c",
                    f'import socket; print(socket.gethostbyname_ex("{self.target.name}"))',
                ],
                network=test_container_network_name,
                remove=True,
            )
            return True
        except ContainerError:
            return False

    def container_in_network(self, container: Container):
        assert container.attrs is not None
        network_names = set(container.attrs["NetworkSettings"].get("Networks", {}).keys())
        return network_names and network_names != {"bridge"}

    def print_suggestion(self, message: str):
        print(f"{self.suggestion_number}: {message}")
        self.suggestion_number += 1

    def ensure_network(self, name: str):
        try:
            self.client.networks.get(name)
        except NotFound:
            self.create_network(name)

    def create_network(self, name: str):
        network = cast(Network, self.client.networks.create(name))
        self._append_cleanup(Cleanup("create_network", lambda: network.remove()))

    def attach_to_network(self, container: Container, network_name: str):
        network = cast(Network, self.client.networks.get(network_name))
        network.connect(container)
        try:
            container.reload()
        finally:
            self._append_cleanup(
                Cleanup("attach_to_network", lambda: network.disconnect(container))
            )

    def _append_cleanup(self, cleanup: Cleanup):
        LOG.debug(f"Adding cleanup {cleanup.name}")
        self.cleanups.append(cleanup)


class GeneralDiagnoser(Diagnoser):
    def perform_connectivity_test(self, test_network_name: str | None = None):
        if self.test_dns(test_network_name):
            # Success
            return

        test_network_name = test_network_name or f"network-{short_uid()}"
        self.ensure_network(test_network_name)
        if not self.container_in_network(self.source):
            self.print_suggestion(f"Add container {self.source.name} to a user-defined network")
            self.attach_to_network(self.source, test_network_name)
            # recurse back into the test
            return self.perform_connectivity_test(test_network_name)

        if not self.container_in_network(self.target):
            self.print_suggestion(f"Add container {self.target.name} to a user-defined network")
            self.attach_to_network(self.target, test_network_name)
            # recurse back into the test
            return self.perform_connectivity_test(test_network_name)

        print("No further suggestions to make")


class LocalStackDiagnoser(Diagnoser):
    def perform_connectivity_test(self, test_network_name: str | None = None):
        if self.test_health_endpoint(test_network_name=test_network_name):
            # check SSL
            if not self.test_health_endpoint(
                test_network_name=test_network_name, protocol=Protocol.https, port=443
            ):
                self.print_suggestion(
                    f"SSL verification is not available when using {self.target.name} as a domain name. Consider using HTTP."
                )

            return

        test_network_name = test_network_name or f"network-{short_uid()}"
        self.ensure_network(test_network_name)
        if not self.container_in_network(self.source):
            self.print_suggestion(f"Add container {self.source.name} to a user-defined network")
            self.attach_to_network(self.source, test_network_name)
            # recurse back into the test
            return self.perform_connectivity_test(test_network_name)

        if not self.container_in_network(self.target):
            self.print_suggestion(f"Add container {self.target.name} to a user-defined network")
            self.attach_to_network(self.target, test_network_name)
            # recurse back into the test
            return self.perform_connectivity_test(test_network_name)

        print("No further suggestions to make")

    def test_health_endpoint(
        self,
        protocol: Protocol = Protocol.http,
        test_network_name: str | None = None,
        port: int = 4566,
    ):
        health_endpoint = f"{protocol}://{self.target.name}:{port}/_localstack/health"

        LOG.debug(f"trying connectivity to {health_endpoint} in network {test_network_name}")

        try:
            self.client.containers.run(
                image="DEBUG_IMAGE_NAME",
                entrypoint="bash",
                command=["-c", f"curl {health_endpoint}"],
                network=test_network_name,
                remove=True,
            )
            return True
        except ContainerError:
            return False


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
    )
    client = DockerClient()
    diagnoser = LocalStackDiagnoser(client, "ls-scenario1-app", "ls-scenario1")
    # diagnoser = LocalStackDiagnoser(
    #     client, "2-no-subdomain-support-application-1", "2-no-subdomain-support-localstack-1"
    # )
    diagnoser.test_connectivity()
