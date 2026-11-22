"""pa11y skill: accessibility testing wrapper.

``run`` wraps the pa11y CLI (clear RuntimeError when the binary is absent —
pa11y needs a browser, so there is no pure-python fallback here; use the
``axe_core`` skill for an offline check). ``issues_summary`` parses pa11y
JSON output into counts by type/code.

Operations: ``run``, ``issues_summary``.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run


def run(url: str, standard: str = "WCAG2AA", extra_args: list | None = None,
        **kwargs: Any) -> dict[str, Any]:
    """Run pa11y against a URL and return its JSON issue list parsed."""
    if shutil.which("pa11y") is None:
        raise RuntimeError("install with: npm install -g pa11y  # requires Node.js")
    cmd = ["pa11y", "--reporter", "json", "--standard", standard,
           *(extra_args or []), url]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    try:
        issues = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"pa11y produced no JSON: {proc.stderr.strip()[:400]}") from exc
    return {"status": "ok", "url": url, "n_issues": len(issues),
            "issues": issues, "returncode": proc.returncode}


def issues_summary(issues: list | None = None, json_path: str | None = None,
                   **kwargs: Any) -> dict[str, Any]:
    """Count pa11y issues by type (error/warning/notice) and code.

    Provide a parsed ``issues`` list or a ``json_path`` to pa11y JSON output.
    """
    if issues is None:
        if json_path is None:
            raise ValueError("Provide 'issues' list or 'json_path'")
        issues = json.loads(Path(json_path).read_text(encoding="utf-8"))
    by_type: dict[str, int] = {}
    by_code: dict[str, int] = {}
    for issue in issues or []:
        t = issue.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
        by_code[issue.get("code", "?")] = by_code.get(issue.get("code", "?"), 0) + 1
    return {"status": "ok", "n_issues": len(issues or []),
            "by_type": by_type, "by_code": by_code}


run = skill_run({"run": run, "issues_summary": issues_summary})
register_skill("pa11y", run)
