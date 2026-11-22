"""sqlfluff skill: SQL linting.

Uses the ``sqlfluff`` CLI when on PATH; otherwise a regex fallback that
flags ``SELECT *`` and ``DELETE``/``UPDATE`` statements without a WHERE
clause.

Operations: ``lint``, ``fix_stub``.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run


def _strip_strings(sql: str) -> str:
    return re.sub(r"'(?:[^']|'')*'|\"(?:[^\"]|\"\")*\"", "''", sql)


def _fallback_lint(sql: str, fname: str) -> list[dict[str, Any]]:
    clean = _strip_strings(sql)
    violations = []
    for m in re.finditer(r"\bSELECT\s+\*", clean, re.IGNORECASE):
        violations.append({
            "file": fname, "line": clean.count("\n", 0, m.start()) + 1,
            "rule": "L043", "description": "Unnecessary wildcard SELECT *",
        })
    for keyword in ("DELETE", "UPDATE"):
        stmt_re = re.compile(
            rf"\b{keyword}\s+FROM\s+[^;]*" if keyword == "DELETE"
            else rf"\bUPDATE\s+[^;]*",
            re.IGNORECASE)
        for m in stmt_re.finditer(clean):
            stmt = m.group()
            if not re.search(r"\bWHERE\b", stmt, re.IGNORECASE):
                violations.append({
                    "file": fname, "line": clean.count("\n", 0, m.start()) + 1,
                    "rule": "L999",
                    "description": f"{keyword} statement without WHERE clause",
                })
    return violations


def _read_sql(path_or_sql: str) -> list[tuple[str, str]]:
    p = Path(path_or_sql)
    if p.is_file():
        return [(str(p), p.read_text(encoding="utf-8", errors="replace"))]
    if p.is_dir():
        return [(str(f), f.read_text(encoding="utf-8", errors="replace"))
                for f in sorted(p.rglob("*.sql"))]
    return [("<inline>", path_or_sql)]


def lint(path: str | None = None, sql: str | None = None, **kwargs: Any) -> dict[str, Any]:
    """Lint SQL from a ``path`` (file/dir) or inline ``sql`` text."""
    target = path if path is not None else sql
    if target is None:
        raise ValueError("Provide 'path' (file/dir) or 'sql' text")
    sources = _read_sql(target)
    if shutil.which("sqlfluff") is not None and path is not None:
        import json

        proc = subprocess.run(["sqlfluff", "lint", "--format", "json", str(path)],
                              capture_output=True, text=True, timeout=300)
        data = json.loads(proc.stdout or "[]")
        violations = [
            {"file": f.get("filepath"), "line": v.get("start_line_no", 0),
             "rule": v.get("code", ""), "description": v.get("description", "")}
            for f in data for v in f.get("violations", [])
        ]
        engine = "sqlfluff"
    else:
        violations = [v for fname, text in sources for v in _fallback_lint(text, fname)]
        engine = "regex-fallback"
    return {"status": "ok", "engine": engine, "n_violations": len(violations),
            "violations": violations}


def fix_stub(path: str | None = None, sql: str | None = None, **kwargs: Any) -> dict[str, Any]:
    """Describe what an auto-fix would change (sqlfluff fix is not run).

    Applies conservative textual fixes in-memory: flags which violations
    could be fixed automatically (currently: none that are always safe) and
    returns the suggested rewrite hints per violation.
    """
    res = lint(path=path, sql=sql)
    hints = []
    for v in res["violations"]:
        if v["rule"] == "L043":
            hints.append({**v, "suggestion": "replace SELECT * with explicit column list"})
        elif v["rule"] == "L999":
            hints.append({**v, "suggestion": "add a WHERE clause or use TRUNCATE for full-table deletes"})
    return {"status": "ok", "auto_fixable": 0,
            "manual_fixes": hints,
            "note": "no unsafe automatic fixes are applied; run 'sqlfluff fix' manually"}


run = skill_run({"lint": lint, "fix_stub": fix_stub})
register_skill("sqlfluff", run)
