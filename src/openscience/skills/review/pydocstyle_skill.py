"""pydocstyle skill: docstring convention checks (pure AST).

Checks that public modules, classes and functions have docstrings.

Operations: ``check``, ``coverage_percent``, ``missing_list``.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run
from openscience.skills.review import _ast_common as ac


def _is_public(name: str) -> bool:
    return not name.startswith("_")


def _check_file(path: Path) -> list[dict[str, Any]]:
    missing = []
    tree = ac.parse_file(path)
    source = ac.read_source(path)
    lines = source.splitlines()
    if ast.get_docstring(tree) is None:
        missing.append({"file": str(path), "line": 1, "kind": "module",
                        "name": path.stem, "code": "D100"})
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and _is_public(node.name):
            if ast.get_docstring(node) is None:
                missing.append({"file": str(path), "line": node.lineno,
                                "kind": "class", "name": node.name, "code": "D101"})
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and _is_public(node.name):
            if ast.get_docstring(node) is None:
                missing.append({"file": str(path), "line": node.lineno,
                                "kind": "function", "name": node.name, "code": "D103"})
    return missing


def _totals(path: Path) -> tuple[int, int]:
    """(documentable public objects, documented public objects) in one file."""
    tree = ac.parse_file(path)
    total = 1  # the module itself
    documented = 1 if ast.get_docstring(tree) else 0
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and _is_public(node.name):
            total += 1
            documented += 1 if ast.get_docstring(node) else 0
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and _is_public(node.name):
            total += 1
            documented += 1 if ast.get_docstring(node) else 0
    return total, documented


def check(path: str, **kwargs: Any) -> dict[str, Any]:
    """Check public module/class/function docstrings under ``path``."""
    files = ac.collect_python_files(path)
    missing = [m for f in files for m in _check_file(f)]
    return {"status": "ok", "files_checked": len(files),
            "n_missing": len(missing), "violations": missing}


def coverage_percent(path: str, **kwargs: Any) -> dict[str, Any]:
    """Percent of public modules/classes/functions that have docstrings."""
    files = ac.collect_python_files(path)
    total = documented = 0
    for f in files:
        t, d = _totals(f)
        total += t
        documented += d
    pct = round(100.0 * documented / total, 2) if total else 100.0
    return {"status": "ok", "coverage_percent": pct,
            "documented": documented, "total": total}


def missing_list(path: str, **kwargs: Any) -> dict[str, Any]:
    """List the public objects lacking docstrings."""
    res = check(path)
    return {"status": "ok", "n_missing": res["n_missing"],
            "missing": [{"file": m["file"], "kind": m["kind"], "name": m["name"],
                         "line": m["line"]} for m in res["violations"]]}


run = skill_run({"check": check, "coverage_percent": coverage_percent,
                 "missing_list": missing_list})
register_skill("pydocstyle", run)
