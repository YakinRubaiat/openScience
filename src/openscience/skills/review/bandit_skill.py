"""bandit skill: static security scan of python source.

Uses the real ``bandit`` CLI (``python -m bandit -f json``) when installed,
otherwise an AST fallback that detects eval/exec usage, asserts outside
tests, ``pickle.loads``, ``subprocess ... shell=True`` and hardcoded
password assignments.

Operations: ``scan``, ``report``.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run
from openscience.skills.review import _ast_common as ac

_PW_NAMES = ("password", "passwd", "pwd", "secret", "api_key", "token")


def _fallback_scan_file(path: Path) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    test_file = ac.is_test_path(path)
    for node in ast.walk(ac.parse_file(path)):
        if isinstance(node, ast.Call):
            name = ac.call_name(node)
            if name in ("eval", "exec"):
                issues.append(_issue(path, node, "B307" if name == "eval" else "B102",
                                     f"use of {name}()", "HIGH"))
            elif name == "pickle.loads" or name.endswith(".pickle.loads"):
                issues.append(_issue(path, node, "B301", "pickle.loads on untrusted data", "MEDIUM"))
            elif name.startswith("subprocess.") or name.endswith("Popen"):
                for kw in node.keywords:
                    if (kw.arg == "shell" and isinstance(kw.value, ast.Constant)
                            and kw.value.value is True):
                        issues.append(_issue(path, node, "B602",
                                             "subprocess with shell=True", "HIGH"))
        elif isinstance(node, ast.Assert) and not test_file:
            issues.append(_issue(path, node, "B101",
                                 "assert used in non-test code", "LOW"))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            value = node.value
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                for t in targets:
                    tname = ac.dotted_name(t).lower()
                    if any(p in tname for p in _PW_NAMES) and value.value:
                        issues.append(_issue(path, node, "B105",
                                             f"hardcoded password string assigned to {tname}",
                                             "LOW"))
    return issues


def _issue(path: Path, node: ast.AST, code: str, text: str, severity: str) -> dict[str, Any]:
    return {
        "filename": str(path),
        "line_number": getattr(node, "lineno", 0),
        "test_id": code,
        "issue_text": text,
        "issue_severity": severity,
    }


def _bandit_available() -> bool:
    return ac.tool_available("bandit")


def scan(path: str, **kwargs: Any) -> dict[str, Any]:
    """Scan python source at ``path`` for security issues."""
    files = ac.collect_python_files(path)
    if _bandit_available():
        data = ac.run_tool_json("bandit", ["-f", "json", "-q", str(path)])
        results = data.get("results", [])
        issues = [
            {
                "filename": r.get("filename"),
                "line_number": r.get("line_number"),
                "test_id": r.get("test_id"),
                "issue_text": r.get("issue_text"),
                "issue_severity": str(r.get("issue_severity", "")).upper(),
            }
            for r in results
        ]
        engine = "bandit"
    else:
        issues = [i for f in files for i in _fallback_scan_file(f)]
        engine = "ast-fallback"
    return {
        "status": "ok",
        "engine": engine,
        "files_scanned": len(files),
        "n_issues": len(issues),
        "issues": issues,
    }


def report(path: str | None = None, issues: list | None = None, **kwargs: Any) -> dict[str, Any]:
    """Severity counts for a scan (pass ``issues`` or a ``path`` to scan)."""
    if issues is None:
        if path is None:
            raise ValueError("Provide 'issues' from a scan or a 'path' to scan")
        issues = scan(path)["issues"]
    counts: dict[str, int] = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for i in issues:
        sev = str(i.get("issue_severity", "")).upper()
        counts[sev] = counts.get(sev, 0) + 1
    return {"status": "ok", "total": len(issues), "by_severity": counts}


run = skill_run({"scan": scan, "report": report})
register_skill("bandit", run)
