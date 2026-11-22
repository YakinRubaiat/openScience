"""network_analysis skill: degree distribution, betweenness, components."""

from __future__ import annotations

from collections import Counter
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import has_module, result, unwrap


def _build(kwargs: dict[str, Any]) -> tuple[list[str], list[tuple[str, str]]]:
    kw = unwrap(kwargs)
    nodes = [str(n) for n in (kw.get("nodes") or [])]
    edges = [(str(a), str(b)) for a, b in (kw.get("edges") or [])]
    for a, b in edges:
        for n in (a, b):
            if n not in nodes:
                nodes.append(n)
    return nodes, edges


def degree_dist(**kwargs: Any) -> dict[str, Any]:
    """Undirected degree distribution {degree: count} (pure)."""
    nodes, edges = _build(kwargs)
    deg: Counter[str] = Counter(n for e in edges for n in e)
    for n in nodes:
        deg.setdefault(n, 0)
    dist = Counter(deg.values())
    return result(distribution={str(k): v for k, v in sorted(dist.items())})


def betweenness_top(**kwargs: Any) -> dict[str, Any]:
    """Top-k nodes by betweenness centrality (networkx; empty without)."""
    kw = unwrap(kwargs)
    nodes, edges = _build(kw)
    k = int(kw.get("k", 5))
    if not has_module("networkx") or not nodes:
        return result(top=[])
    import networkx as nx

    g = nx.Graph()
    g.add_nodes_from(nodes)
    g.add_edges_from(edges)
    bc = nx.betweenness_centrality(g)
    top = sorted(bc.items(), key=lambda t: t[1], reverse=True)[:k]
    return result(top=[{"node": n, "betweenness": round(float(v), 6)} for n, v in top])


def connected_components(**kwargs: Any) -> dict[str, Any]:
    """Connected components of the undirected graph (pure union-find)."""
    nodes, edges = _build(kwargs)
    parent = {n: n for n in nodes}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in edges:
        parent[find(a)] = find(b)
    groups: dict[str, list[str]] = {}
    for n in nodes:
        groups.setdefault(find(n), []).append(n)
    comps = [sorted(g) for g in groups.values()]
    comps.sort(key=len, reverse=True)
    return result(components=comps, n_components=len(comps))


_OPS = {
    "degree_dist": degree_dist,
    "betweenness_top": betweenness_top,
    "connected_components": connected_components,
}


def run(operation: str = "run", **kwargs: Any) -> dict[str, Any]:
    """Dispatch to an operation; ``run`` defaults to ``degree_dist``."""
    op = _OPS.get(operation) or _OPS["degree_dist"]
    if operation not in _OPS and operation != "run":
        raise ValueError(f"Unknown operation {operation!r}. Available: {sorted(_OPS)}")
    return op(**kwargs)


register_skill("network_analysis", run)
