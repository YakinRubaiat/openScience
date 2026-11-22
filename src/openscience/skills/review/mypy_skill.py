"""mypy skill: static type checking.

``typecheck``/``summary`` use ``python -m mypy`` when mypy is installed and
raise a clear RuntimeError otherwise. ``count_annotated_functions`` is a
pure-AST annotation-coverage check that always works.

Operations: ``typecheck``, ``summary``, ``count_annotated_functions``.
"""

from __future__ import annotations

import ast
import json
import re
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run
from openscience.skills.review import _ast_common as ac


def run_mypy_json_lines(path: str) -> list[dict[str, Any]]:
    """Run mypy and parse output lines into structured messages."""
    proc = ac.run_tool("mypy", ["--no-error-summary", "--show-column-numbers", str(path)])
    messages = []
    line_re = re.compile(r"^(.*?):(\d+):(\d+):\s*(error|warning|note):\s*(.*)$")
    for line in proc.stdout.splitlines():
        m = line_re.match(line)
        if m:
            f, row, col, severity, text = m.groups()
            messages.append({"file": f, "line": int(row), "column": int(col),
                             "severity": severity, "message": text})
    return messages


def typecheck(path: str, **kwargs: Any) -> dict[str, Any]:
    """Type-check python source at ``path`` with mypy."""
    ac.require_tool("mypy")
    files = ac.collect_python_files(path)
    try:
        messages = run_mypy_json_lines(path)
    except json.JSONDecodeError:  # pragma: no cover - defensive
        messages = []
    n_errors = sum(1 for m in messages if m["severity"] == "error")
    return {
        "status": "ok" if n_errors == 0 else "error",
        "engine": "mypy",
        "files_checked": len(files),
        "n_errors": n_errors,
        "messages": messages,
    }


def summary(path: str, **kwargs: Any) -> dict[str, Any]:
    """Error-count summary grouped by file."""
    res = typecheck(path)
    by_file: dict[str, int] = {}
    for m in res["messages"]:
        if m["severity"] == "error":
            by_file[m["file"]] = by_file.get(m["file"], 0) + 1
    return {"status": "ok", "n_errors": res["n_errors"], "errors_by_file": by_file}


def count_annotated_functions(path: str, **kwargs: Any) -> dict[str, Any]:
    """Annotation coverage: functions with all args + return annotated."""
    files = ac.collect_python_files(path)
    total = annotated = 0
    per_file = []
    for f in files:
        tree = ac.parse_file(f)
        f_total = f_ann = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                f_total += 1
                args = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
                args = [a for a in args if a.arg not in ("self", "cls")]
                args_ok = all(a.annotation is not None for a in args)
                vararg_ok = node.args.vararg is None or node.args.vararg.annotation is not None
                kwarg_ok = node.args.kwarg is None or node.args.kwarg.annotation is not None
                ret_ok = node.returns is not None
                if args_ok and vararg_ok and kwarg_ok and ret_ok:
                    f_ann += 1
        total += f_total
        annotated += f_ann
        per_file.append({"file": str(f), "functions": f_total, "annotated": f_ann})
    pct = round(100.0 * annotated / total, 2) if total else 100.0
    return {"status": "ok", "engine": "ast", "n_functions": total,
            "n_annotated": annotated, "coverage_percent": pct, "files": per_file}


run = skill_run({"typecheck": typecheck, "summary": summary,
                 "count_annotated_functions": count_annotated_functions})
register_skill("mypy", run)
