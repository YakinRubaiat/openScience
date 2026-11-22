"""interrogate skill: docstring coverage statistics (pure AST).

Counts documentable objects (modules, classes, methods, functions) and how
many carry a docstring, per file and overall.

Operations: ``coverage``, ``badge_level``.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run
from openscience.skills.review import _ast_common as ac


def _file_stats(path: Path) -> dict[str, Any]:
    tree = ac.parse_file(path)
    total = 1  # module
    documented = 1 if ast.get_docstring(tree) else 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            total += 1
            documented += 1 if ast.get_docstring(node) else 0
    pct = round(100.0 * documented / total, 2) if total else 100.0
    return {"file": str(path), "total": total, "documented": documented,
            "coverage_percent": pct}


def coverage(path: str, **kwargs: Any) -> dict[str, Any]:
    """Docstring coverage per file and overall for source at ``path``."""
    files = ac.collect_python_files(path)
    stats = [_file_stats(f) for f in files]
    total = sum(s["total"] for s in stats)
    documented = sum(s["documented"] for s in stats)
    pct = round(100.0 * documented / total, 2) if total else 100.0
    return {"status": "ok", "overall_percent": pct, "n_documented": documented,
            "n_total": total, "files": stats}


def badge_level(path: str | None = None, percent: float | None = None,
                **kwargs: Any) -> dict[str, Any]:
    """Badge colour for a coverage percent (or computed from ``path``)."""
    if percent is None:
        if path is None:
            raise ValueError("Provide 'percent' or a 'path' to compute it")
        percent = coverage(path)["overall_percent"]
    if percent >= 90:
        level = "brightgreen"
    elif percent >= 75:
        level = "green"
    elif percent >= 60:
        level = "yellow"
    elif percent >= 40:
        level = "orange"
    else:
        level = "red"
    return {"status": "ok", "percent": percent, "badge_color": level,
            "badge_text": f"docstring coverage {percent:.0f}%"}


run = skill_run({"coverage": coverage, "badge_level": badge_level})
register_skill("interrogate", run)
