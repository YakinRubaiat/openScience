"""architecture_rules skill: enforce module-dependency rules (pure AST).

Checks forbidden-import rules against the actual import graph, detects
cyclic packages, and reports module fan-out.

Operations: ``check_layer_rule``, ``cyclic_packages``, ``module_fan_out_report``.
"""

from __future__ import annotations

from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run
from openscience.skills.review import _ast_common as ac


def _matches(module: str, pattern: str) -> bool:
    return module == pattern or module.startswith(pattern + ".")


def check_layer_rule(path: str, rules: list | None = None,
                     module: str | None = None, forbidden: list | None = None,
                     **kwargs: Any) -> dict[str, Any]:
    """Check forbidden-import rules against source at ``path``.

    ``rules`` entries: ``{"module": "<package prefix>", "forbidden": ["x", ...]}``
    — meaning modules under the prefix must not import the listed packages.
    Alternatively pass a single ``module`` + ``forbidden`` pair.
    """
    if rules is None:
        if module is None or forbidden is None:
            raise ValueError("Provide 'rules' or 'module'+'forbidden'")
        rules = [{"module": module, "forbidden": forbidden}]
    graph = ac.import_graph(path)
    violations = []
    for rule in rules:
        prefix = str(rule.get("module", ""))
        banned = list(rule.get("forbidden", []))
        for mod, deps in graph.items():
            mod_suffix = mod.split(".", 1)[-1] if "." in mod else mod
            if not (_matches(mod, prefix) or _matches(mod_suffix, prefix)
                    or mod.endswith("." + prefix) or mod_suffix == prefix):
                continue
            for dep in deps:
                if any(_matches(dep, b) for b in banned):
                    violations.append({"module": mod, "imports": dep,
                                       "rule": f"{prefix} may not import {banned}"})
    return {"status": "ok", "passed": not violations,
            "n_violations": len(violations), "violations": violations}


def cyclic_packages(path: str | None = None, graph: dict | None = None,
                    **kwargs: Any) -> dict[str, Any]:
    """Import cycles among first-level packages at ``path``."""
    if graph is None:
        if path is None:
            raise ValueError("Provide 'graph' or a 'path'")
        raw = ac.import_graph(path)
    else:
        raw = {m: set(d) for m, d in graph.items()}
    local_tops = {m.split(".")[0] for m in raw}
    pkg_graph: dict[str, set[str]] = {}
    for mod, deps in raw.items():
        top = mod.split(".")[0]
        targets = pkg_graph.setdefault(top, set())
        for dep in deps:
            dtop = dep.split(".")[0]
            if dtop in local_tops and dtop != top:
                targets.add(dtop)
    cycles = ac.find_cycles(pkg_graph)
    packages = sorted({p for cyc in cycles for p in cyc})
    return {"status": "ok", "n_cycles": len(cycles), "cycles": cycles,
            "packages_in_cycles": packages}


def module_fan_out_report(path: str, top: int | None = None, **kwargs: Any) -> dict[str, Any]:
    """Fan-out (number of distinct imports) per module, descending."""
    graph = ac.import_graph(path)
    report = [{"module": m, "fan_out": len(deps), "imports": sorted(deps)}
              for m, deps in sorted(graph.items())]
    report.sort(key=lambda r: r["fan_out"], reverse=True)
    if top is not None:
        report = report[: int(top)]
    return {"status": "ok", "n_modules": len(report), "modules": report}


run = skill_run({"check_layer_rule": check_layer_rule,
                 "cyclic_packages": cyclic_packages,
                 "module_fan_out_report": module_fan_out_report})
register_skill("architecture_rules", run)
