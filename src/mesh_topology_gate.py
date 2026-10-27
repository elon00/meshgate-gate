"""Deterministic, offline undirected mesh topology invariant checker.

No network probes, consensus, cryptography, RPC, or deployment claims.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

NODE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
MAX_NODES = 1000
MAX_LINKS = 10000
MAX_BYTES = 1_000_000


class TopologyError(ValueError):
    """Input or graph invariant failure."""


def validate(topology):
    if type(topology) is not dict or set(topology) != {"nodes", "links"}:
        raise TopologyError("EXPECTED_NODES_AND_LINKS")
    nodes, links = topology["nodes"], topology["links"]
    if type(nodes) is not list or not 1 <= len(nodes) <= MAX_NODES:
        raise TopologyError("INVALID_NODE_COUNT")
    if any(type(n) is not str or not NODE_ID.fullmatch(n) for n in nodes):
        raise TopologyError("INVALID_NODE_ID")
    if len(set(nodes)) != len(nodes):
        raise TopologyError("DUPLICATE_NODE")
    if type(links) is not list or len(links) > MAX_LINKS:
        raise TopologyError("INVALID_LINK_COUNT")

    known = set(nodes)
    adjacency = {n: set() for n in nodes}
    edges = set()
    for link in links:
        if type(link) is not list or len(link) != 2 or any(type(x) is not str for x in link):
            raise TopologyError("INVALID_LINK")
        a, b = link
        if a not in known or b not in known:
            raise TopologyError("UNKNOWN_ENDPOINT")
        if a == b:
            raise TopologyError("SELF_LINK")
        edge = tuple(sorted((a, b)))
        if edge in edges:
            raise TopologyError("DUPLICATE_LINK")
        edges.add(edge)
        adjacency[a].add(b)
        adjacency[b].add(a)

    visited = {nodes[0]}
    stack = [nodes[0]]
    while stack:
        for neighbor in adjacency[stack.pop()]:
            if neighbor not in visited:
                visited.add(neighbor)
                stack.append(neighbor)
    if len(visited) != len(nodes):
        raise TopologyError("PARTITION_DETECTED")

    canonical = json.dumps(
        {"nodes": sorted(nodes), "links": sorted([list(e) for e in edges])},
        sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    )
    return {
        "status": "PASS_OFFLINE_TOPOLOGY_ONLY",
        "node_count": len(nodes),
        "link_count": len(edges),
        "topology_sha256": hashlib.sha256(canonical.encode("ascii")).hexdigest(),
    }


def _reject_duplicate_keys(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise TopologyError("DUPLICATE_JSON_KEY")
        obj[key] = value
    return obj


def _reject_constant(value):
    raise TopologyError("NONSTANDARD_JSON_NUMBER")


def read_topology(path):
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise TopologyError("INPUT_TOO_LARGE")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys,
                      parse_constant=_reject_constant)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline mesh graph invariant check; NOT a live network probe")
    parser.add_argument("file", help="JSON file with nodes and undirected links")
    args = parser.parse_args(argv)
    try:
        result = validate(read_topology(args.file))
    except (TopologyError, ValueError, UnicodeError, OSError) as exc:
        print(f"FAIL_OFFLINE_TOPOLOGY: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
