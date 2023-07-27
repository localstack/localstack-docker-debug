from __future__ import annotations

import json
import logging
from pathlib import Path
import sys
from typing import cast, Iterable

import click
from click.exceptions import ClickException
from docker import DockerClient
from docker.errors import NotFound
from docker.models.containers import Container

from dockerdebug.probe import Prober, ProbeDefn
from dockerdebug.diagnose import GeneralDiagnoser, LocalStackDiagnoser
from dockerdebug.connectivity import (
    can_connect_to_localstack_health_endpoint,
    CustomEncoder,
)
from dockerdebug.render import render_graph

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
)
LOG = logging.getLogger("dockerdebug")
LOG.setLevel(logging.WARNING)


class CannotFindLocalStackContainer(Exception):
    pass


class MultipleLocalStackContainerCandidates(Exception):
    def __init__(self, candidates: set[Container]):
        self.candidates = candidates


def _containers_with_localstack_labels(
    containers: Iterable[Container],
) -> set[Container]:
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


@click.group
@click.option("-v", "--verbose", is_flag=True, default=False)
def main(verbose: bool):
    if verbose:
        LOG.setLevel(logging.DEBUG)


@main.command
@click.option(
    "-s",
    "--source-container",
    "source_container_id",
    help="Container to test connectivity from",
    required=True,
)
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
def diagnose(source_container_id: str, target_container_id: str | None, target_is_localstack: bool):
    """
    Determine why your application container cannot access another container.
    """
    client = DockerClient()

    source_container = cast(Container, client.containers.get(source_container_id))

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
        diagnoser = LocalStackDiagnoser(client, source_container, target_container)
    else:
        diagnoser = GeneralDiagnoser(client, source_container, target_container)

    diagnoser.test_connectivity()


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


# test is an internal command that is not very useful on its own, but when run from a docker container with a specific networking configuration, it evaluates connectivity between containers.
@main.command
@click.option(
    "-t",
    "--target-container",
    "target_container_id",
    required=True,
    help="Container to test connectivity to. If not specified, assume LocalStack",
)
@click.option(
    "-l",
    "--localstack",
    "target_is_localstack",
    help="Assume target container is localstack",
    is_flag=True,
)
def test(target_container_id: str, target_is_localstack: bool):
    """
    Test connectivity to another container.
    """
    if not target_is_localstack:
        raise ClickException("TODO")

    result = {
        "connectivity": can_connect_to_localstack_health_endpoint(target_container_id),
    }
    json.dump(result, sys.stdout, cls=CustomEncoder)


@main.command
@click.option("-f", "--filename", help="File to render", type=Path, required=True)
def render(filename: Path):
    """
    Render a network graph
    """
    with filename.open() as infile:
        top: ProbeDefn = json.load(infile)

    render_graph(top)


if __name__ == "__main__":
    main()
