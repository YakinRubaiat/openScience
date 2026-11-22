"""Network analysis skill backed by networkx.

Skill name: ``networkx``. Operations:

- ``from_edges``        — build a graph from an edge list
- ``degree_centrality`` — node degree centrality
- ``betweenness``       — betweenness centrality
- ``pagerank``          — PageRank scores
- ``communities``       — greedy modularity communities
- ``enrich_subnetwork`` — Fisher-exact enrichment of a query set in a subnetwork
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import stats

from openscience.skills import register_skill
from openscience.skills._common import optional_import, unwrap


def _nx():
    return optional_import("networkx")


def _to_graph(G=None, edges=None, directed: bool = False):
    nx = _nx()
    if G is not None:
        if not isinstance(G, (nx.Graph, nx.DiGraph)):
            raise TypeError("'graph' must be a networkx Graph/DiGraph")
        return G
    if edges is None:
        raise ValueError("Provide either 'graph' or 'edges'")
    g = nx.DiGraph() if directed else nx.Graph()
    for e in edges:
        if isinstance(e, dict):
            g.add_edge(e["source"], e["target"], weight=e.get("weight", 1.0))
        else:
            if len(e) < 2:
                raise ValueError(f"Edge must have at least 2 nodes, got {e!r}")
            g.add_edge(e[0], e[1], weight=float(e[2]) if len(e) > 2 else 1.0)
    return g


def from_edges(edges=None, directed: bool = False, context: dict | None = None, **kwargs: Any):
    kw = unwrap(kwargs)
    edges = edges if edges is not None else kw.get("edges")
    directed = bool(kw.get("directed", directed))
    g = _to_graph(edges=edges, directed=directed)
    if context is None:
        context = kw.get("context")
    if isinstance(context, dict):
        context.setdefault("graph", g)
    return {
        "n_nodes": g.number_of_nodes(),
        "n_edges": g.number_of_edges(),
        "directed": g.is_directed(),
        "nodes": sorted(str(n) for n in g.nodes())[:1000],
    }


def degree_centrality(graph=None, edges=None, **kwargs: Any):
    kw = unwrap(kwargs)
    g = _to_graph(graph or kw.get("graph") or _context_graph(kw), edges or kw.get("edges"))
    nx = _nx()
    cent = nx.degree_centrality(g)
    top = sorted(cent.items(), key=lambda kv: kv[1], reverse=True)[: int(kw.get("top", 20))]
    return {
        "n_nodes": g.number_of_nodes(),
        "mean_degree": float(2 * g.number_of_edges() / max(g.number_of_nodes(), 1)),
        "top_nodes": [{"node": str(n), "centrality": float(c)} for n, c in top],
    }


def betweenness(graph=None, edges=None, **kwargs: Any):
    kw = unwrap(kwargs)
    g = _to_graph(graph or kw.get("graph") or _context_graph(kw), edges or kw.get("edges"))
    nx = _nx()
    cent = nx.betweenness_centrality(g)
    top = sorted(cent.items(), key=lambda kv: kv[1], reverse=True)[: int(kw.get("top", 20))]
    return {
        "n_nodes": g.number_of_nodes(),
        "top_nodes": [{"node": str(n), "betweenness": float(c)} for n, c in top],
    }


def pagerank(graph=None, edges=None, **kwargs: Any):
    kw = unwrap(kwargs)
    g = _to_graph(graph or kw.get("graph") or _context_graph(kw), edges or kw.get("edges"))
    nx = _nx()
    pr = nx.pagerank(g, alpha=float(kw.get("alpha", 0.85)))
    top = sorted(pr.items(), key=lambda kv: kv[1], reverse=True)[: int(kw.get("top", 20))]
    return {
        "n_nodes": g.number_of_nodes(),
        "top_nodes": [{"node": str(n), "pagerank": float(c)} for n, c in top],
    }


def communities(graph=None, edges=None, **kwargs: Any):
    kw = unwrap(kwargs)
    g = _to_graph(graph or kw.get("graph") or _context_graph(kw), edges or kw.get("edges"))
    nx = _nx()
    ug = g.to_undirected() if g.is_directed() else g
    comms = list(nx.algorithms.community.greedy_modularity_communities(ug))
    modularity = (
        float(nx.algorithms.community.modularity(ug, comms)) if comms else 0.0
    )
    return {
        "n_communities": len(comms),
        "modularity": modularity,
        "community_sizes": sorted((len(c) for c in comms), reverse=True),
        "communities": [sorted(str(n) for n in c) for c in comms[:50]],
    }


def enrich_subnetwork(graph=None, edges=None, query_nodes=None, **kwargs: Any):
    """Fisher-exact test: is the query set enriched among subnetwork nodes?"""
    kw = unwrap(kwargs)
    g = _to_graph(graph or kw.get("graph") or _context_graph(kw), edges or kw.get("edges"))
    query = query_nodes or kw.get("query_nodes")
    sub = kw.get("subnetwork_nodes")
    if query is None:
        raise ValueError("enrich_subnetwork requires 'query_nodes'")
    query = set(query)
    universe = set(g.nodes())
    if sub is None:
        # default subnetwork: the ego-network (query nodes + their neighbours)
        sub = set(query) | {n for q in query if q in g for n in g.neighbors(q)}
    else:
        sub = set(sub)
    a = len(query & sub)
    b = len(query - sub)
    c = len(sub - query)
    d = max(len(universe) - a - b - c, 0)
    odds, p = stats.fisher_exact([[a, b], [c, d]], alternative="greater")
    return {
        "query_size": len(query),
        "subnetwork_size": len(sub),
        "overlap": sorted(str(n) for n in (query & sub)),
        "overlap_size": a,
        "odds_ratio": float(odds) if np.isfinite(odds) else None,
        "p_value": float(p),
    }


def _context_graph(kw: dict):
    ctx = kw.get("context")
    if isinstance(ctx, dict):
        return ctx.get("graph")
    return None


def run(operation: str, **kwargs: Any):
    ops = {
        "from_edges": from_edges,
        "degree_centrality": degree_centrality,
        "betweenness": betweenness,
        "pagerank": pagerank,
        "communities": communities,
        "enrich_subnetwork": enrich_subnetwork,
    }
    fn = ops.get(operation)
    if fn is None:
        raise ValueError(f"networkx: unknown operation {operation!r}. Available: {sorted(ops)}")
    if operation == "from_edges":
        return fn(**kwargs)
    return fn(**kwargs)


register_skill("networkx", run)
