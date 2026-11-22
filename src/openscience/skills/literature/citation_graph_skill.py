"""citation_graph skill: build a citation graph and compute basic stats.

Builds a networkx DiGraph when available, otherwise a plain adjacency dict.
"""

from __future__ import annotations

from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import has_module, result, unwrap


def _build_adjacency(papers: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Adjacency: paper_id -> list of referenced paper ids (and vice nodes)."""
    adj: dict[str, list[str]] = {}
    for p in papers:
        pid = str(p.get("paper_id") or p.get("pmid") or p.get("doi") or "")
        if not pid:
            continue
        refs = [str(r) for r in (p.get("references") or p.get("refs") or [])]
        adj.setdefault(pid, [])
        adj[pid].extend(refs)
        for r in refs:
            adj.setdefault(r, [])
    return adj


def build(**kwargs: Any) -> dict[str, Any]:
    """Build a citation graph from papers (pure). Returns edges + nodes."""
    papers = unwrap(kwargs).get("papers") or []
    adj = _build_adjacency(papers)
    edges = [(a, b) for a, refs in adj.items() for b in refs]
    out: dict[str, Any] = result(
        nodes=sorted(adj.keys()), edges=[list(e) for e in edges], n_edges=len(edges)
    )
    if has_module("networkx"):
        import networkx as nx

        g = nx.DiGraph()
        g.add_nodes_from(adj.keys())
        g.add_edges_from(edges)
        out["n_nodes"] = g.number_of_nodes()
    else:
        out["n_nodes"] = len(adj)
    return out


def centrality(**kwargs: Any) -> dict[str, Any]:
    """In-degree (citation) centrality per node (pure; nx used if present)."""
    papers = unwrap(kwargs).get("papers") or []
    adj = _build_adjacency(papers)
    edges = [(a, b) for a, refs in adj.items() for b in refs]
    if has_module("networkx"):
        import networkx as nx

        g = nx.DiGraph()
        g.add_nodes_from(adj.keys())
        g.add_edges_from(edges)
        cent = {n: round(float(v), 6) for n, v in nx.in_degree_centrality(g).items()}
    else:
        n = max(len(adj) - 1, 1)
        in_deg = {node: 0 for node in adj}
        for _a, b in edges:
            in_deg[b] = in_deg.get(b, 0) + 1
        cent = {node: round(deg / n, 6) for node, deg in in_deg.items()}
    return result(centrality=cent)


def citation_counts(**kwargs: Any) -> dict[str, Any]:
    """Count incoming citations per paper from the reference lists (pure)."""
    papers = unwrap(kwargs).get("papers") or []
    adj = _build_adjacency(papers)
    counts: dict[str, int] = {}
    for refs in adj.values():
        for r in refs:
            counts[r] = counts.get(r, 0) + 1
    return result(counts=counts)


_OPS = {"build": build, "centrality": centrality, "citation_counts": citation_counts}


def run(operation: str = "run", **kwargs: Any) -> dict[str, Any]:
    """Dispatch to an operation; ``run`` defaults to ``build``."""
    op = _OPS.get(operation) or _OPS["build"]
    if operation not in _OPS and operation != "run":
        raise ValueError(f"Unknown operation {operation!r}. Available: {sorted(_OPS)}")
    return op(**kwargs)


register_skill("citation_graph", run)
