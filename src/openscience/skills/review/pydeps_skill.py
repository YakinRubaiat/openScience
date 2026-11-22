"""pydeps skill: import-graph exploration (pure AST).

Builds a module->imports graph from python source, finds dependency cycles
via DFS, and renders the graph as Graphviz DOT.

Operations: ``import_graph``, ``find_cycles``, ``to_dot``.
"""

from __future__ import annotations

from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run
from openscience.skills.review import _ast_common as ac


def import_graph(path: str, local_only: bool = True, **kwargs: Any) -> dict[str, Any]:
    """Module import graph for source at ``path``.

    With ``local_only`` (default), external/stdlib imports are dropped.
    """
    graph = ac.import_graph(path)
    if local_only:
        local_roots = {m.split(".")[0] for m in graph} | set(graph)
        graph = {m: {d for d in deps
                     if d.split(".")[0] in local_roots or d.startswith(".")}
                 for m, deps in graph.items()}
    return {"status": "ok", "n_modules": len(graph),
            "graph": {m: sorted(deps) for m, deps in sorted(graph.items())}}


def find_cycles(path: str | None = None, graph: dict | None = None,
                **kwargs: Any) -> dict[str, Any]:
    """Import cycles in the graph at ``path`` (or a supplied ``graph``)."""
    if graph is None:
        if path is None:
            raise ValueError("Provide 'graph' or a 'path'")
        graph = {m: set(d) for m, d in import_graph(path)["graph"].items()}
    else:
        graph = {m: set(d) for m, d in graph.items()}
    cycles = ac.find_cycles(graph)
    return {"status": "ok", "n_cycles": len(cycles), "cycles": cycles}


def to_dot(path: str | None = None, graph: dict | None = None,
           external: bool = False, **kwargs: Any) -> dict[str, Any]:
    """Render the import graph as Graphviz DOT text."""
    if graph is None:
        if path is None:
            raise ValueError("Provide 'graph' or a 'path'")
        g = ac.import_graph(path) if external else {
            m: set(d) for m, d in import_graph(path)["graph"].items()}
    else:
        g = {m: set(d) for m, d in graph.items()}
    lines = ["digraph imports {"]
    lines.append('  rankdir="LR";')
    for mod in sorted(g):
        deps = g[mod]
        if not deps:
            lines.append(f'  "{mod}";')
        for dep in sorted(deps):
            lines.append(f'  "{mod}" -> "{dep}";')
    lines.append("}")
    return {"status": "ok", "n_edges": sum(len(d) for d in g.values()),
            "dot": "\n".join(lines)}


run = skill_run({"import_graph": import_graph, "find_cycles": find_cycles,
                 "to_dot": to_dot})
register_skill("pydeps", run)
