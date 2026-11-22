"""darglint skill: docstring/signature parameter consistency (pure AST).

Verifies that every parameter in a function signature is documented in the
docstring's ``Args:``/``Parameters`` section (Google or NumPy style).

Operations: ``check_docstring_params``, ``report``.
"""

from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run
from openscience.skills.review import _ast_common as ac

_SECTION_RE = re.compile(
    r"(?:^|\n)\s*(?:Args|Arguments|Parameters)\s*:\s*\n(.*?)(?:\n\s*(?:Returns|Yields|Raises|"
    r"Attributes|Examples?|Notes|See Also|Warnings)\s*:|\Z)", re.DOTALL)
_GOOGLE_PARAM_RE = re.compile(r"^\s*(\*{0,2}[A-Za-z_][\w]*)\s*(?:\(|:)", re.MULTILINE)
_NUMPY_PARAM_RE = re.compile(r"^\s*(\*{0,2}[A-Za-z_][\w]*)\s*:\s*\S", re.MULTILINE)


def _docstring_params(doc: str) -> set[str]:
    section = _SECTION_RE.search(doc)
    if not section:
        return set()
    body = section.group(1)
    names = set(_GOOGLE_PARAM_RE.findall(body)) | set(_NUMPY_PARAM_RE.findall(body))
    return {n.lstrip("*") for n in names}


def _signature_params(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    args = node.args
    params = [a.arg for a in (*args.posonlyargs, *args.args, *args.kwonlyargs)]
    params = [p for p in params if p not in ("self", "cls")]
    if args.vararg:
        params.append(args.vararg.arg)
    if args.kwarg:
        params.append(args.kwarg.arg)
    return params


def _check_file(path: Path) -> list[dict[str, Any]]:
    findings = []
    for node in ast.walk(ac.parse_file(path)):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        doc = ast.get_docstring(node)
        if doc is None:
            continue  # missing docstring is pydocstyle's job
        try:
            inspect.cleandoc(doc)  # sanity parse
        except Exception:
            pass
        documented = _docstring_params(doc)
        expected = _signature_params(node)
        missing = [p for p in expected if p not in documented]
        extra = [p for p in documented if p not in expected]
        for p in missing:
            findings.append({"file": str(path), "line": node.lineno,
                             "function": node.name, "code": "DAR101",
                             "message": f"parameter {p!r} missing from docstring"})
        for p in extra:
            findings.append({"file": str(path), "line": node.lineno,
                             "function": node.name, "code": "DAR102",
                             "message": f"docstring documents unknown parameter {p!r}"})
    return findings


def check_docstring_params(path: str, **kwargs: Any) -> dict[str, Any]:
    """Check that documented functions document all their parameters."""
    files = ac.collect_python_files(path)
    findings = [f for p in files for f in _check_file(p)]
    return {"status": "ok", "files_checked": len(files),
            "n_findings": len(findings), "findings": findings}


def report(path: str, **kwargs: Any) -> dict[str, Any]:
    """Findings grouped per file."""
    res = check_docstring_params(path)
    per_file: dict[str, int] = {}
    for f in res["findings"]:
        per_file[f["file"]] = per_file.get(f["file"], 0) + 1
    return {"status": "ok", "n_findings": res["n_findings"], "per_file": per_file}


run = skill_run({"check_docstring_params": check_docstring_params, "report": report})
register_skill("darglint", run)
