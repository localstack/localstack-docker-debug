import socket
import ssl
from typing import Iterable, cast

import dns.resolver
import dns.rdatatype
import dns.rrset
from docker import DockerClient
from docker.models.containers import Container


TEST_DNS_NAMES = [
    "host.localstack.cloud",
    "host.docker.internal",
    "localhost.localstack.cloud",
    "example.com",
    "s3.amazonaws.com",
]


# https://www.askpython.com/python/python-program-to-verify-ssl-certificates
def verify_ssl_certificate(hostname: str, port: int = 443) -> bool:
    context = ssl.create_default_context()

    try:
        with socket.create_connection((hostname, port)) as sock:
            try:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    ssock.do_handshake()
                    ssock.getpeercert()
                    return True
            except ssl.SSLCertVerificationError:
                return False
    except ConnectionRefusedError:
        return False


class NoDomain:
    def __init__(self, question: str):
        self.question = question

    def __repr__(self) -> str:
        return f"{self.question}: NO_DOMAIN"


def resolve_name(name: str) -> dns.rrset.RRset | NoDomain:
    try:
        answer = dns.resolver.resolve(name, rdtype=dns.rdatatype.A)
        return answer.rrset or NoDomain(name)
    except dns.resolver.NXDOMAIN:
        return NoDomain(name)


class CannotFindLocalStackContainer(Exception):
    pass


class MultipleLocalStackContainerCandidates(Exception):
    def __init__(self, candidates: set[str]):
        self.candidates = candidates


def _containers_with_localstack_labels(containers: Iterable[Container]) -> set[str]:
    candidates = set()
    for container in containers:
        if container.labels.get("authors") == "LocalStack Contributors":
            candidates.add(container.id)
            continue
    return candidates


def _containers_with_exposed_ports(containers: Iterable[Container]) -> set[str]:
    candidates = set()
    for container in containers:
        if "4566/tcp" in container.ports:
            candidates.add(container.id)
    return candidates


def find_localstack_container(containers: Iterable[Container]) -> str:
    candidates: set[str] = set()
    candidates = candidates.union(_containers_with_localstack_labels(containers))
    candidates = candidates.union(_containers_with_exposed_ports(containers))
    if len(candidates) == 1:
        return list(candidates)[0]
    elif len(candidates) == 0:
        raise CannotFindLocalStackContainer()
    else:
        raise MultipleLocalStackContainerCandidates(candidates)


if __name__ == "__main__":
    print("Starting")

    client = DockerClient()
    containers = cast(list[Container], client.containers.list())
    ls_container_id = find_localstack_container(containers)
    print(f"Found local stack container id: {ls_container_id}")

    print("Done")
