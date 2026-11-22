"""pylint skill: lint python source.

Uses ``python -m pylint --output-format=json`` when pylint is installed,
otherwise an AST fallback detecting unused imports, unused local variables
in functions, and functions with too many arguments (>6).

Operations: ``lint``, ``score``.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run
from openscience.skills.review import _ast_common as ac

MAX_ARGS = 6


class _FallbackLinter(ast.NodeVisitor):
    def __init__(self, path: Path):
        self.path = path
        self.messages: list[dict[str, Any]] = []

    def _msg(self, node: ast.AST, code: str, symbol: str, text: str) -> None:
        self.messages.append({
            "path": str(self.path), "line": getattr(node, "lineno", 0),
            "message-id": code, "symbol": symbol, "message": text,
        })

    def visit(self, tree: ast.AST) -> None:  # type: ignore[override]
        if isinstance(tree, ast.Module):
            self._check_unused_imports(tree)
        super().visit(tree)

    def _check_unused_imports(self, tree: ast.AST) -> None:
        imported: dict[str, ast.AST] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    imported[(a.asname or a.name.split(".")[0])] = node
            elif isinstance(node, ast.ImportFrom):
                for a in node.names:
                    if a.name != "*":
                        imported[a.asname or a.name] = node
        used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        used |= {ac.dotted_name(n).split(".")[0] for n in ast.walk(tree)
                 if isinstance(n, ast.Attribute)}
        for name, node in imported.items():
            if name not in used:
                self._msg(node, "W0611", "unused-import", f"Unused import {name}")

    def _check_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        args = node.args
        n_args = len(args.posonlyargs) + len(args.args) + len(args.kwonlyargs)
        if n_args > MAX_ARGS:
            self._msg(node, "R0913", "too-many-arguments",
                      f"Too many arguments ({n_args}/{MAX_ARGS})")
        assigned: dict[str, ast.AST] = {}
        for sub in ast.walk(node):
            if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and sub is not node:
                continue  # nested scopes handle themselves
            if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                assigned.setdefault(sub.id, sub)
            elif isinstance(sub, ast.arg):
                assigned.setdefault(sub.arg, sub)
        loaded = {n.id for n in ast.walk(node)
                  if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
        argnames = {a.arg for a in (*args.posonlyargs, *args.args, *args.kwonlyargs)}
        for name, sub in assigned.items():
            if name not in loaded and name not in argnames and not name.startswith("_"):
                self._msg(sub, "W0612", "unused-variable", f"Unused variable {name!r}")

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_function(node)
        self.generic_visit(node)


def _pylint_available() -> bool:
    return ac.tool_available("pylint")


def lint(path: str, **kwargs: Any) -> dict[str, Any]:
    """Lint python source at ``path``."""
    files = ac.collect_python_files(path)
    if _pylint_available():
        proc = ac.run_tool("pylint", ["--output-format=json", "--score=n", str(path)])
        import json

        out = proc.stdout.strip()
        messages = json.loads(out) if out else []
        engine = "pylint"
    else:
        messages: list[dict[str, Any]] = []
        for f in files:
            try:
                linter = _FallbackLinter(f)
                linter.visit(ac.parse_file(f))
                messages.extend(linter.messages)
            except ValueError as exc:
                messages.append({"path": str(f), "line": 0, "message-id": "E0001",
                                 "symbol": "syntax-error", "message": str(exc)})
        engine = "ast-fallback"
    return {
        "status": "ok",
        "engine": engine,
        "files_linted": len(files),
        "n_messages": len(messages),
        "messages": messages,
    }


def score(path: str | None = None, messages: list | None = None, **kwargs: Any) -> dict[str, Any]:
    """Pylint-style 0-10 score from lint messages (10 - 5*messages/file)."""
    if messages is None:
        if path is None:
            raise ValueError("Provide 'messages' from lint or a 'path' to lint")
        res = lint(path)
        messages, n_files = res["messages"], max(res["files_linted"], 1)
    else:
        n_files = len({m.get("path") for m in messages}) or 1
    value = max(0.0, 10.0 - 5.0 * len(messages) / n_files)
    return {"status": "ok", "score": round(value, 2), "n_messages": len(messages)}


run = skill_run({"lint": lint, "score": score})
register_skill("pylint", run)
