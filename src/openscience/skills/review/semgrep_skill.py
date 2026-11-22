"""semgrep skill: pattern-based static scan.

Uses the real ``semgrep`` CLI when on PATH; otherwise an AST fallback that
evaluates a small rule schema (dicts with ``id``, ``message``, ``severity``
and a ``pattern`` of ``dangerous-import``/``call``/``print-call``).

Operations: ``scan``, ``list_rules``.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run
from openscience.skills.review import _ast_common as ac

DEFAULT_RULES: list[dict[str, Any]] = [
    {
        "id": "dangerous-imports",
        "message": "import of a dangerous module",
        "severity": "WARNING",
        "pattern": {"kind": "import", "modules": ["pickle", "marshal", "subprocess", "os.system"]},
    },
    {
        "id": "print-in-lib-code",
        "message": "print() call in library code; use logging",
        "severity": "INFO",
        "pattern": {"kind": "print-call"},
    },
    {
        "id": "dangerous-calls",
        "message": "call to a dangerous function",
        "severity": "ERROR",
        "pattern": {"kind": "call", "names": ["eval", "exec", "os.system", "commands.getoutput"]},
    },
]


def _match_rule(tree: ast.AST, path: Path, rule: dict[str, Any]) -> list[dict[str, Any]]:
    pat = rule.get("pattern", {})
    kind = pat.get("kind", "")
    hits: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        matched = False
        detail = ""
        if kind == "import" and isinstance(node, (ast.Import, ast.ImportFrom)):
            mods = set(pat.get("modules", []))
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            else:
                names = [node.module or ""]
            for n in names:
                if n in mods or any(n.startswith(m + ".") for m in mods):
                    matched, detail = True, n
        elif kind == "print-call" and isinstance(node, ast.Call):
            if ac.call_name(node) == "print":
                matched, detail = True, "print"
        elif kind == "call" and isinstance(node, ast.Call):
            name = ac.call_name(node)
            if name in pat.get("names", []):
                matched, detail = True, name
        if matched:
            hits.append({
                "rule_id": rule.get("id", "unknown"),
                "path": str(path),
                "line": getattr(node, "lineno", 0),
                "message": f"{rule.get('message', '')} ({detail})",
                "severity": rule.get("severity", "INFO"),
            })
    return hits


def _semgrep_available() -> bool:
    import shutil

    return shutil.which("semgrep") is not None


def scan(path: str, rules: list | None = None, **kwargs: Any) -> dict[str, Any]:
    """Scan ``path`` with semgrep or the AST fallback rule engine."""
    files = ac.collect_python_files(path)
    rules = rules if rules is not None else DEFAULT_RULES
    if _semgrep_available() and rules is DEFAULT_RULES:
        import json
        import subprocess

        proc = subprocess.run(
            ["semgrep", "scan", "--json", "--config", "auto", str(path)],
            capture_output=True, text=True, timeout=300,
        )
        data = json.loads(proc.stdout or "{}")
        hits = [
            {
                "rule_id": r.get("check_id"),
                "path": r.get("path"),
                "line": r.get("start", {}).get("line", 0),
                "message": r.get("extra", {}).get("message", ""),
                "severity": r.get("extra", {}).get("severity", "INFO"),
            }
            for r in data.get("results", [])
        ]
        engine = "semgrep"
    else:
        hits = []
        for f in files:
            try:
                tree = ac.parse_file(f)
            except ValueError:
                continue
            for rule in rules:
                hits.extend(_match_rule(tree, f, rule))
        engine = "ast-fallback"
    return {
        "status": "ok",
        "engine": engine,
        "files_scanned": len(files),
        "n_findings": len(hits),
        "findings": hits,
    }


def list_rules(**kwargs: Any) -> dict[str, Any]:
    """List the built-in fallback rules."""
    return {"status": "ok", "n_rules": len(DEFAULT_RULES),
            "rules": [{k: r[k] for k in ("id", "message", "severity")} for r in DEFAULT_RULES]}


run = skill_run({"scan": scan, "list_rules": list_rules})
register_skill("semgrep", run)
