"""Shared helpers for review skills: python source collection, subprocess
wrappers, and small AST utilities used by the fallback implementations."""

from __future__ import annotations

import ast
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def collect_python_files(path: str | Path) -> list[Path]:
    """Return sorted ``*.py`` files under ``path`` (or the single file)."""
    p = Path(path)
    if p.is_file():
        if p.suffix != ".py":
            raise ValueError(f"Not a python file: {p}")
        return [p]
    if not p.is_dir():
        raise FileNotFoundError(f"Path not found: {p}")
    return sorted(f for f in p.rglob("*.py") if f.is_file())


def read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_file(path: Path) -> ast.AST:
    """Parse a python file, raising ValueError with the syntax error message."""
    try:
        return ast.parse(read_source(path), filename=str(path))
    except SyntaxError as exc:
        raise ValueError(f"Cannot parse {path}: {exc}") from exc


def tool_available(name: str) -> bool:
    """True when a CLI tool is importable as a module or on PATH."""
    import importlib.util

    return importlib.util.find_spec(name) is not None or shutil.which(name) is not None


def require_tool(name: str, package: str | None = None) -> None:
    """Raise RuntimeError with an install hint when the tool is missing."""
    if not tool_available(name):
        raise RuntimeError(f"install with: pip install {package or name}")


def run_tool(module: str, args: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    """Run ``python -m <module> <args>``; never raises on non-zero exit."""
    return subprocess.run(
        [sys.executable, "-m", module, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def run_tool_json(module: str, args: list[str], timeout: int = 120) -> Any:
    """Run a tool expecting JSON on stdout; raise RuntimeError otherwise."""
    proc = run_tool(module, args, timeout=timeout)
    out = proc.stdout.strip()
    if not out:
        raise RuntimeError(
            f"{module} produced no JSON output: {proc.stderr.strip()[:400]}"
        )
    start = min((i for i in (out.find("{"), out.find("[")) if i >= 0))
    return json.loads(out[start:])


def dotted_name(node: ast.AST | None) -> str:
    """Best-effort dotted name for Name/Attribute nodes, '' otherwise."""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value  # type: ignore[assignment]
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def call_name(node: ast.Call) -> str:
    """Dotted name of the callable being invoked (e.g. 'pickle.loads')."""
    return dotted_name(node.func)


def is_test_path(path: Path) -> bool:
    """Heuristic: files named test_* or living in a tests/ directory."""
    parts = {p.lower() for p in path.parts}
    return path.name.startswith("test_") or "tests" in parts or "test" in parts


def import_graph(path: str | Path) -> dict[str, set[str]]:
    """Module -> set of imported module names, built with the AST.

    Module keys are path-derived dotted names relative to ``path`` when it is
    a directory, else the file stem.
    """
    p = Path(path)
    files = collect_python_files(p)
    graph: dict[str, set[str]] = {}
    for f in files:
        if p.is_dir():
            mod = ".".join(f.relative_to(p).with_suffix("").parts)
        else:
            mod = f.stem
        deps = graph.setdefault(mod, set())
        try:
            tree = parse_file(f)
        except ValueError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    deps.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    deps.add("." * node.level + (node.module or ""))
                elif node.module:
                    deps.add(node.module)
    return graph


def find_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    """All elementary cycles found via DFS, each as a list of nodes."""
    cycles: list[list[str]] = []
    seen_cycles: set[tuple[str, ...]] = set()

    def canonical(cyc: list[str]) -> tuple[str, ...]:
        i = cyc.index(min(cyc))
        return tuple(cyc[i:] + cyc[:i])

    def dfs(node: str, stack: list[str], on_stack: set[str]) -> None:
        stack.append(node)
        on_stack.add(node)
        for nxt in graph.get(node, ()):
            if nxt not in graph:
                continue
            if nxt in on_stack:
                cyc = stack[stack.index(nxt):]
                key = canonical(cyc)
                if key not in seen_cycles:
                    seen_cycles.add(key)
                    cycles.append(list(key))
            else:
                dfs(nxt, stack, on_stack)
        stack.pop()
        on_stack.discard(node)

    for n in sorted(graph):
        dfs(n, [], set())
    return cycles
