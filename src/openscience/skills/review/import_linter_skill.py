"""import_linter skill: layered import-contract checks (pure AST).

Given a layered contract (lower layers must not import from higher ones),
verifies actual imports in python source against it.

Config example::

    {"layers": ["db", "services", "api"], "root_package": "myapp"}

means ``myapp.api`` may import ``myapp.services`` and ``myapp.db``, but
``myapp.db`` may not import ``myapp.services`` or ``myapp.api``.

Operations: ``check_contracts``, ``violations``.
"""

from __future__ import annotations

from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run
from openscience.skills.review import _ast_common as ac


def _layer_of(module: str, layers: list[str], root: str) -> int | None:
    """Index of the layer ``module`` belongs to, or None if outside."""
    prefix = f"{root}." if root else ""
    for i, layer in enumerate(layers):
        full = prefix + layer
        if module == full or module.startswith(full + "."):
            return i
    return None


def _check(path: str, layers: list[str], root_package: str = "") -> list[dict[str, Any]]:
    """Lower index = lower layer; a layer may only import layers below it."""
    graph = ac.import_graph(path)
    # graph modules are path-derived; strip the leading root dir component
    violations = []
    for module, deps in graph.items():
        candidates = [module]
        if root_package and module.startswith(root_package + "."):
            candidates.append(module[len(root_package) + 1:])
        from_idx = next((i for m in candidates
                         if (i := _layer_of(m, layers, root_package)) is not None), None)
        if from_idx is None:
            # try matching on the tail of the module path
            tail = module.split(".", 1)[-1]
            from_idx = _layer_of(f"{root_package + '.' if root_package else ''}{tail}",
                                 layers, root_package)
        if from_idx is None:
            continue
        for dep in deps:
            to_idx = _layer_of(dep, layers, root_package)
            if to_idx is not None and to_idx > from_idx:
                violations.append({
                    "module": module,
                    "layer": layers[from_idx],
                    "imports": dep,
                    "imports_layer": layers[to_idx],
                    "message": (f"{layers[from_idx]!r} must not import from "
                                f"higher layer {layers[to_idx]!r}"),
                })
    return violations


def check_contracts(path: str, layers: list, root_package: str = "",
                    **kwargs: Any) -> dict[str, Any]:
    """Verify the layered import contract on source at ``path``."""
    if not isinstance(layers, list) or len(layers) < 2:
        raise ValueError("'layers' must be a list of at least two layer names")
    found = _check(path, list(layers), root_package)
    return {"status": "ok", "kept": not found, "n_violations": len(found),
            "violations": found}


def violations(path: str, layers: list, root_package: str = "", **kwargs: Any) -> dict[str, Any]:
    """Module->bad-import grouped view of contract violations."""
    res = check_contracts(path, layers, root_package)
    by_module: dict[str, list[str]] = {}
    for v in res["violations"]:
        by_module.setdefault(v["module"], []).append(v["imports"])
    return {"status": "ok", "kept": res["kept"], "n_violations": res["n_violations"],
            "by_module": by_module}


run = skill_run({"check_contracts": check_contracts, "violations": violations})
register_skill("import_linter", run)
