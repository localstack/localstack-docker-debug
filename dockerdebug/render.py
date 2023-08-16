import ipaddress
import itertools
from collections import defaultdict
import random
import tempfile
from typing import Tuple

import graphviz

from dockerdebug.probe import ContainerDefn, NetworkDefn, ProbeDefn

# lazy
from dockerdebug.diagnose import short_uid

NODE_ID: int = 0


def shuffle(arr):
    random.shuffle(arr)
    return arr


COLOURS = itertools.cycle(
    shuffle(
        [
            "#1f78b4",
            "#33a02c",
            "#e31a1c",
            "#ff7f00",
            "#6a3d9a",
            "#b15928",
            "#a6cee3",
            "#b2df8a",
            "#fdbf6f",
            "#cab2d6",
            "#ffff99",
        ]
    )
)


def next_colour() -> str:
    return next(COLOURS)


def calculate_text_colour(background_colour: str) -> str:
    r = int(background_colour[1:3], 16)
    g = int(background_colour[3:5], 16)
    b = int(background_colour[5:7], 16)
    value = (r + g + b) / (3 * 255)
    assert 0 <= value <= 1
    if value > 0.5:
        return "black"
    else:
        return "white"


def container_name_and_label(
    network: NetworkDefn, container: ContainerDefn
) -> Tuple[str, str, str]:
    global NODE_ID
    name = f'{container["name"]}_{short_uid()}'

    # strict here does not fail when host bits are set
    # likely a windows thing
    network_subnet = ipaddress.IPv4Network(network["subnet"], strict=False)

    ip_addresses = []
    for interface in container["interfaces"]:
        ip_address = ipaddress.IPv4Address(interface["ip_address"])
        if ip_address in network_subnet:
            ip_addresses.append(str(ip_address))

    ip_addresses = ", ".join(ip_addresses)

    label = f"{name} - {ip_addresses}"

    NODE_ID += 1
    return container["name"], name, label


def compute_container_colours(topology: ProbeDefn) -> dict[str, str]:
    mapping = {}
    for network in topology["networks"]:
        for container in network["containers"]:
            container_name = container["name"]
            if container_name in mapping:
                continue

            mapping[container_name] = next_colour()
    return mapping


def render_graph(topology: ProbeDefn):
    container_colours = compute_container_colours(topology)

    dot = graphviz.Graph()

    name_node_mapping = defaultdict(list)
    for i, network in enumerate(topology["networks"]):
        network_name = f'{network["name"]} - {network["subnet"]}'
        if len(network["containers"]) == 0:
            continue

        with dot.subgraph(name=f"cluster_{i}", graph_attr={"label": network_name}) as g:
            for container in network["containers"]:
                name, node_name, label = container_name_and_label(network, container)
                colour = container_colours[name]
                text_colour = calculate_text_colour(colour)
                g.node(
                    node_name, label=label, fillcolor=colour, fontcolor=text_colour, style="filled"
                )
                name_node_mapping[name].append(node_name)

    # only draw one edge per pair
    seen_edges = set()
    for _, node_names in name_node_mapping.items():
        if len(node_names) > 1:
            for a, b in itertools.permutations(node_names):
                if (b, a) in seen_edges:
                    continue
                dot.edge(a, b)
                seen_edges.add((a, b))

    with tempfile.NamedTemporaryFile("r+t") as outfile:
        dot.render(outfile.name)
        outfile.seek(0)
        contents = outfile.read()

    print(contents)
