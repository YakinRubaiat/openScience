"""graph_visualization skill: circular/spring layouts, PNG draw, Gephi CSV."""

from __future__ import annotations

import base64
import io
import math
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import has_module, result, unwrap


def _edges_nodes(kwargs: dict[str, Any]) -> tuple[list[str], list[tuple[str, str]]]:
    kw = unwrap(kwargs)
    nodes = [str(n) for n in (kw.get("nodes") or [])]
    edges = [(str(a), str(b)) for a, b in (kw.get("edges") or [])]
    for a, b in edges:
        for n in (a, b):
            if n not in nodes:
                nodes.append(n)
    return nodes, edges


def spring_layout_coords(**kwargs: Any) -> dict[str, Any]:
    """Node coordinates: networkx spring layout, or circular fallback (pure)."""
    nodes, edges = _edges_nodes(kwargs)
    if not nodes:
        return result(coords={})
    if has_module("networkx"):
        import networkx as nx

        g = nx.Graph()
        g.add_nodes_from(nodes)
        g.add_edges_from(edges)
        pos = nx.spring_layout(g, seed=42)
        coords = {n: [round(float(x), 4), round(float(y), 4)] for n, (x, y) in pos.items()}
    else:
        m = len(nodes)
        coords = {
            n: [round(math.cos(2 * math.pi * i / m), 4), round(math.sin(2 * math.pi * i / m), 4)]
            for i, n in enumerate(sorted(nodes))
        }
    return result(coords=coords)


def draw(**kwargs: Any) -> dict[str, Any]:
    """Render the graph to a PNG (matplotlib) and return base64."""
    kw = unwrap(kwargs)
    coords = spring_layout_coords(**kw).get("coords", {})
    _nodes, edges = _edges_nodes(kw)
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(5, 4))
    for a, b in edges:
        if a in coords and b in coords:
            ax.plot(
                [coords[a][0], coords[b][0]], [coords[a][1], coords[b][1]],
                color="#999999", linewidth=0.8, zorder=1,
            )
    for n, (x, y) in coords.items():
        ax.scatter([x], [y], s=80, zorder=2, color="#4C72B0")
        ax.annotate(n, (x, y), fontsize=7, ha="center", va="bottom")
    ax.axis("off")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    plt.close(fig)
    return result(png_base64=base64.b64encode(buf.getvalue()).decode("ascii"))


def to_gephi_csv(**kwargs: Any) -> dict[str, Any]:
    """Export nodes+edges as Gephi-compatible CSV strings (pure)."""
    nodes, edges = _edges_nodes(kwargs)
    nodes_csv = "Id,Label\n" + "\n".join(f"{n},{n}" for n in sorted(nodes))
    edges_csv = "Source,Target\n" + "\n".join(f"{a},{b}" for a, b in edges)
    return result(nodes_csv=nodes_csv, edges_csv=edges_csv)


_OPS = {
    "spring_layout_coords": spring_layout_coords,
    "draw": draw,
    "to_gephi_csv": to_gephi_csv,
}


def run(operation: str = "run", **kwargs: Any) -> dict[str, Any]:
    """Dispatch to an operation; ``run`` defaults to ``spring_layout_coords``."""
    op = _OPS.get(operation) or _OPS["spring_layout_coords"]
    if operation not in _OPS and operation != "run":
        raise ValueError(f"Unknown operation {operation!r}. Available: {sorted(_OPS)}")
    return op(**kwargs)


register_skill("graph_visualization", run)
