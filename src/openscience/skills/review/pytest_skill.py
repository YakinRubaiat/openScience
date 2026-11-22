"""pytest skill: run and summarise pytest suites.

Wraps the real ``pytest`` CLI via subprocess; raises a clear RuntimeError
when pytest is not importable.

Operations: ``run_collection_only``, ``run_short``, ``report``.
"""

from __future__ import annotations

import re
import subprocess
import sys
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run
from openscience.skills.review import _ast_common as ac

_SUMMARY_RE = re.compile(
    r"(?:(\d+) passed)?[,\s]*(?:(\d+) failed)?[,\s]*(?:(\d+) skipped)?[,\s]*"
    r"(?:(\d+) error)?[,\s]*(?:(\d+) warnings?)?", re.IGNORECASE)


def _pytest_available() -> bool:
    return ac.tool_available("pytest")


def _summary_counts(output: str) -> dict[str, int]:
    counts = {"passed": 0, "failed": 0, "skipped": 0, "error": 0, "warnings": 0}
    for line in reversed(output.splitlines()):
        if " in " not in line and "=" not in line:
            continue
        if not any(k in line for k in ("passed", "failed", "skipped", "error")):
            continue
        for num, name in re.findall(r"(\d+)\s+(passed|failed|skipped|errors?|warnings?)", line):
            key = "error" if name.startswith("error") else name.rstrip("s")
            if key in counts or key == "warning":
                counts["warnings" if key == "warning" else key] += int(num)
        if re.search(r"\d+\s+(passed|failed|skipped|error)", line):
            break
    return counts


def run_collection_only(path: str = ".", **kwargs: Any) -> dict[str, Any]:
    """Collect tests without running them (``pytest --collect-only -q``)."""
    ac.require_tool("pytest")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", path],
        capture_output=True, text=True, timeout=300)
    tests = [l for l in proc.stdout.splitlines()
             if l.strip() and "::" in l and "no tests ran" not in l]
    return {"status": "ok" if proc.returncode in (0, 5) else "error",
            "n_collected": len(tests), "tests": tests,
            "returncode": proc.returncode}


def run_short(path: str = ".", extra_args: list | None = None, **kwargs: Any) -> dict[str, Any]:
    """Run ``pytest -x --tb=short`` and parse the summary line."""
    ac.require_tool("pytest")
    cmd = [sys.executable, "-m", "pytest", "-x", "--tb=short", "-q", path,
           *(extra_args or [])]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    counts = _summary_counts(proc.stdout)
    return {"status": "ok" if proc.returncode == 0 else "failed",
            "returncode": proc.returncode, **counts,
            "tail": "\n".join((proc.stdout.splitlines() or [""])[-25:])}


def report(path: str = ".", extra_args: list | None = None, **kwargs: Any) -> dict[str, Any]:
    """Full run plus pass-rate report."""
    res = run_short(path, extra_args=["--tb=line"] if extra_args is None else extra_args)
    ran = res["passed"] + res["failed"] + res["error"]
    pass_rate = round(100.0 * res["passed"] / ran, 2) if ran else 0.0
    return {"status": "ok", "pass_rate_percent": pass_rate,
            "counts": {k: res[k] for k in ("passed", "failed", "skipped", "error", "warnings")},
            "returncode": res["returncode"]}


run = skill_run({"run_collection_only": run_collection_only,
                 "run_short": run_short, "report": report})
register_skill("pytest", run)
