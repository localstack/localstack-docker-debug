from __future__ import annotations
from typing import TypeVar, TypedDict, cast, Generator

from docker import DockerClient
from docker.models.containers import Container
from docker.models.networks import Network


T = TypeVar("T")


def _try_get_at_index(l: list[T], index: int, default: T | None = None) -> T | None:
    try:
        return l[index]
    except IndexError:
        return default if default is not None else None


class NetworkDefn(TypedDict):
    id: str
    name: str
    subnet: str | None
    gateway: str | None
    containers: list[ContainerDefn]


class InterfaceDefn(TypedDict):
    network_name: str
    gateway: str
    ip_address: str


class ContainerDefn(TypedDict):
    id: str
    name: str
    labels: dict[str, str]
    status: str
    interfaces: list[InterfaceDefn]


class ProbeDefn(TypedDict):
    networks: list[NetworkDefn]


class Prober:
    def __init__(self, client: DockerClient):
        self.client = client

    def probe(self) -> ProbeDefn:
        networks = []
        for docker_network in cast(list[Network], self.client.networks.list(greedy=True)):
            assert docker_network.attrs is not None
            network: NetworkDefn = {
                "id": docker_network.id or "",
                "name": docker_network.name or "",
                "subnet": _try_get_at_index(docker_network.attrs["IPAM"]["Config"], 0, {}).get(
                    "Subnet"
                ),
                "gateway": _try_get_at_index(docker_network.attrs["IPAM"]["Config"], 0, {}).get(
                    "Gateway"
                ),
                "containers": [
                    self._extract_container_info(container)
                    for container in docker_network.containers
                ],
            }
            networks.append(network)

        return {"networks": networks}

    def _extract_container_info(self, docker_container: Container) -> ContainerDefn:
        container: ContainerDefn = {
            "id": docker_container.id or "",
            "name": docker_container.name or "",
            "image": ", ".join(docker_container.image.tags),
            "labels": docker_container.labels,
            "status": docker_container.status,
            "interfaces": list(self._list_interfaces(docker_container)),
        }
        return container

    def _list_interfaces(self, container: Container) -> Generator[InterfaceDefn, None, None]:
        assert container.attrs is not None

        for name, defn in container.attrs.get("NetworkSettings", {}).get("Networks", {}).items():
            interface: InterfaceDefn = {
                "network_name": name,
                "gateway": defn.get("Gateway", ""),
                "ip_address": defn.get("IPAddress", ""),
            }
            yield interface
