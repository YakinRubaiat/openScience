"""pipdeptree skill: installed-package dependency tree.

Uses ``pipdeptree --json-tree`` when the CLI is on PATH, otherwise reads
installed distribution metadata (Requires-Dist) via importlib.metadata.

Operations: ``tree``, ``reverse_deps``.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from importlib import metadata
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run


def _fallback_tree() -> dict[str, list[str]]:
    tree: dict[str, list[str]] = {}
    for dist in metadata.distributions():
        name = (dist.metadata.get("Name") or dist.name or "").lower()
        if not name:
            continue
        deps = []
        requires = dist.requires if callable(dist.requires) else getattr(dist, "requires", None)
        if callable(requires):
            reqs = requires() or []
        elif isinstance(requires, list):
            reqs = requires
        else:
            reqs = []
        for req in reqs:
            m = re.match(r"\s*([A-Za-z0-9_.\-]+)", req)
            if m and "extra ==" not in req:
                deps.append(m.group(1).lower())
        tree[name] = sorted(set(deps))
    return tree


def _cli_tree() -> dict[str, list[str]]:
    proc = subprocess.run(["pipdeptree", "--json-tree"], capture_output=True,
                          text=True, timeout=120)
    data = json.loads(proc.stdout or "[]")
    tree: dict[str, list[str]] = {}

    def walk(node: dict[str, Any]) -> None:
        tree[node["package"]["key"].lower()] = sorted(
            c["package"]["key"].lower() for c in node.get("dependencies", []))
        for child in node.get("dependencies", []):
            walk(child)

    for top in data:
        walk(top)
    return tree


def tree(packages: list | None = None, **kwargs: Any) -> dict[str, Any]:
    """Dependency tree of installed packages (all or a subset)."""
    graph = _cli_tree() if shutil.which("pipdeptree") else _fallback_tree()
    if packages:
        wanted = {p.lower() for p in packages}
        graph = {k: v for k, v in graph.items() if k in wanted}
    return {"status": "ok", "n_packages": len(graph),
            "tree": {k: v for k, v in sorted(graph.items())}}


def reverse_deps(package: str, **kwargs: Any) -> dict[str, Any]:
    """Installed packages that (transitively) depend on ``package``."""
    graph = _cli_tree() if shutil.which("pipdeptree") else _fallback_tree()
    target = package.lower()
    reverse: dict[str, set[str]] = {}
    for pkg, deps in graph.items():
        for dep in deps:
            reverse.setdefault(dep, set()).add(pkg)
    # transitive closure of reverse edges
    seen: set[str] = set()
    stack = [target]
    while stack:
        node = stack.pop()
        for parent in reverse.get(node, ()):
            if parent not in seen:
                seen.add(parent)
                stack.append(parent)
    return {"status": "ok", "package": target,
            "n_reverse_dependencies": len(seen),
            "reverse_dependencies": sorted(seen)}


run = skill_run({"tree": tree, "reverse_deps": reverse_deps})
register_skill("pipdeptree", run)
