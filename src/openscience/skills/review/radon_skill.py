"""radon skill: cyclomatic complexity and maintainability index.

Uses ``python -m radon`` when installed, otherwise a pure-AST cyclomatic
complexity computation (count of decision nodes + 1 per function).

Operations: ``complexity``, ``mi_report``, ``cc_histogram``.
"""

from __future__ import annotations

import ast
import math
from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run
from openscience.skills.review import _ast_common as ac

_DECISION_NODES: tuple[type[ast.AST], ...] = (
    ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler,
    ast.With, ast.AsyncWith, ast.Assert, ast.IfExp, ast.Match,
)


def cyclomatic_complexity(node: ast.AST) -> int:
    """McCabe complexity of a function/class/module subtree."""
    cc = 1
    for sub in ast.walk(node):
        if isinstance(sub, _DECISION_NODES):
            cc += 1
        elif isinstance(sub, ast.BoolOp):
            cc += len(sub.values) - 1
        elif isinstance(sub, ast.comprehension):
            cc += len(sub.ifs)
    return cc


def _rank(cc: int) -> str:
    for limit, rank in ((5, "A"), (10, "B"), (20, "C"), (30, "D"), (40, "E")):
        if cc <= limit:
            return rank
    return "F"


def _cc_fallback(path: Path) -> list[dict[str, Any]]:
    results = []
    for node in ast.walk(ac.parse_file(path)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            cc = cyclomatic_complexity(node)
            results.append({
                "name": node.name, "type": "function", "file": str(path),
                "lineno": node.lineno, "complexity": cc, "rank": _rank(cc),
            })
    return results


def _mi_fallback(path: Path) -> dict[str, Any]:
    """Simplified MI: 100 - penalties for complexity and comment scarcity."""
    source = ac.read_source(path)
    tree = ac.parse_file(path)
    funcs = [n for n in ast.walk(tree)
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    avg_cc = (sum(cyclomatic_complexity(f) for f in funcs) / len(funcs)) if funcs else 1.0
    lines = max(len([l for l in source.splitlines() if l.strip()]), 1)
    comments = sum(1 for l in source.splitlines() if l.strip().startswith("#"))
    mi = max(0.0, 100.0 - 3.0 * avg_cc - 0.05 * lines + 10.0 * math.log1p(comments + 1))
    return {"file": str(path), "mi": round(mi, 2),
            "rank": "A" if mi >= 80 else "B" if mi >= 60 else "C" if mi >= 40 else "D"}


def _radon_available() -> bool:
    return ac.tool_available("radon")


def complexity(path: str, **kwargs: Any) -> dict[str, Any]:
    """Cyclomatic complexity per function for python source at ``path``."""
    files = ac.collect_python_files(path)
    if _radon_available():
        data = ac.run_tool_json("radon", ["cc", "-j", str(path)])
        results = [
            {**entry, "file": fname}
            for fname, entries in data.items() for entry in entries
        ]
        engine = "radon"
    else:
        results = [r for f in files for r in _cc_fallback(f)]
        engine = "ast-fallback"
    return {"status": "ok", "engine": engine, "n_functions": len(results),
            "functions": results}


def mi_report(path: str, **kwargs: Any) -> dict[str, Any]:
    """Maintainability index per file."""
    files = ac.collect_python_files(path)
    if _radon_available():
        data = ac.run_tool_json("radon", ["mi", "-j", str(path)])
        report = [{"file": f, "mi": round(v.get("mi", 0.0), 2), "rank": v.get("rank", "?")}
                  for f, v in data.items()]
        engine = "radon"
    else:
        report = [_mi_fallback(f) for f in files]
        engine = "ast-fallback"
    return {"status": "ok", "engine": engine, "files": report}


def cc_histogram(path: str | None = None, functions: list | None = None,
                 **kwargs: Any) -> dict[str, Any]:
    """Histogram of complexity ranks (A-F) for ``path`` or ``functions``."""
    if functions is None:
        if path is None:
            raise ValueError("Provide 'functions' from complexity or a 'path'")
        functions = complexity(path)["functions"]
    hist: dict[str, int] = {}
    for f in functions:
        rank = f.get("rank") or _rank(int(f.get("complexity", 1)))
        hist[rank] = hist.get(rank, 0) + 1
    return {"status": "ok", "histogram": {r: hist.get(r, 0) for r in "ABCDEF"},
            "n_functions": len(functions)}


run = skill_run({"complexity": complexity, "mi_report": mi_report,
                 "cc_histogram": cc_histogram})
register_skill("radon", run)
