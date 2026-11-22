"""lineage_tracking skill: in-memory data lineage graph."""

from __future__ import annotations

import time
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run

# Process-wide in-memory lineage store: artifact id -> record.
_GRAPH: dict[str, dict[str, Any]] = {}


def record(artifact: str, step: str, parents: list[str] | None = None,
           metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    """Record that ``artifact`` was produced by ``step`` from ``parents``.

    Builds a DAG in memory; unknown parents are registered as source nodes.
    """
    if not artifact:
        raise ValueError("record requires a non-empty 'artifact' id")
    parents = list(parents or [])
    for parent in parents:
        if parent not in _GRAPH:
            _GRAPH[parent] = {
                "artifact": parent, "step": "source",
                "parents": [], "metadata": {},
                "timestamp": time.time(),
            }
    _GRAPH[artifact] = {
        "artifact": artifact,
        "step": step,
        "parents": parents,
        "metadata": dict(metadata or {}),
        "timestamp": time.time(),
    }
    return result(artifact=artifact, step=step,
                  parents=parents, n_nodes=len(_GRAPH))


def get_lineage(artifact: str | None = None) -> dict[str, Any]:
    """Return the ancestors of ``artifact`` (or the full graph when omitted)."""
    if artifact is None:
        return result(n_nodes=len(_GRAPH),
                      nodes=[dict(v) for v in _GRAPH.values()])
    if artifact not in _GRAPH:
        raise KeyError(f"Unknown artifact {artifact!r}")
    ancestors: list[dict[str, Any]] = []
    seen: set[str] = set()
    stack = [artifact]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        node = _GRAPH.get(current)
        if node is None:
            continue
        ancestors.append(dict(node))
        stack.extend(node["parents"])
    return result(artifact=artifact, n_nodes=len(ancestors), ancestors=ancestors)


def to_dict() -> dict[str, Any]:
    """Export the whole lineage graph as nodes/edges (JSON-friendly)."""
    nodes = [dict(v) for v in _GRAPH.values()]
    edges = [
        {"from": parent, "to": node["artifact"]}
        for node in _GRAPH.values() for parent in node["parents"]
    ]
    return result(n_nodes=len(nodes), n_edges=len(edges),
                  nodes=nodes, edges=edges)


def clear() -> dict[str, Any]:
    """Reset the in-memory lineage graph."""
    n = len(_GRAPH)
    _GRAPH.clear()
    return result(cleared=n)


_OPS = {"record": record, "get_lineage": get_lineage, "to_dict": to_dict, "clear": clear}

run = skill_run(_OPS)
register_skill("lineage_tracking", run)
