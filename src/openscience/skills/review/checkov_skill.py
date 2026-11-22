"""checkov skill: IaC static analysis wrapper.

``scan`` shells out to the checkov CLI (clear RuntimeError when absent).
``parse_results`` summarises checkov JSON output offline.

Operations: ``scan``, ``parse_results``.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run


def scan(path: str, framework: str | None = None, timeout: int = 600,
         **kwargs: Any) -> dict[str, Any]:
    """Run ``checkov -d <path> --output json`` and parse the result."""
    if shutil.which("checkov") is None:
        raise RuntimeError("install with: pip install checkov")
    if not Path(path).exists():
        raise FileNotFoundError(f"Path not found: {path}")
    cmd = ["checkov", "-d", path, "--output", "json", "--quiet"]
    if framework:
        cmd += ["--framework", framework]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if not proc.stdout.strip():
        raise RuntimeError(f"checkov failed: {proc.stderr.strip()[:400]}")
    return parse_results(report=proc.stdout)


def parse_results(report: str | None = None, path: str | None = None,
                  **kwargs: Any) -> dict[str, Any]:
    """Summarise checkov JSON: failed/passed/skipped counts and failures.

    Provide checkov JSON as ``report`` text or a ``path`` to the file.
    """
    if report is None:
        if path is None:
            raise ValueError("Provide checkov 'report' JSON text or a 'path'")
        report = Path(path).read_text(encoding="utf-8")
    data = json.loads(report)
    summary = data.get("summary") or {}
    results = data.get("results") or {}
    failed = [
        {
            "check_id": r.get("check_id", ""),
            "check_name": r.get("check_name", ""),
            "file": r.get("file_path", ""),
            "line": (r.get("file_line_range") or [None])[0],
            "resource": r.get("resource", ""),
        }
        for r in results.get("failed_checks") or []
    ]
    return {
        "status": "ok",
        "passed": int(summary.get("passed", len(results.get("passed_checks") or []))),
        "failed": int(summary.get("failed", len(failed))),
        "skipped": int(summary.get("skipped", 0)),
        "n_failed_checks": len(failed),
        "failed_checks": failed,
    }


run = skill_run({"scan": scan, "parse_results": parse_results})
register_skill("checkov", run)
