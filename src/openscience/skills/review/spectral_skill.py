"""spectral skill: OpenAPI style linting.

Uses the ``spectral`` CLI when on PATH; otherwise a python fallback that
checks path naming (kebab-case segments), operation summaries/descriptions,
and parameter descriptions.

Operations: ``lint``, ``report``.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run
from openscience.skills.review.openapi_validator import _HTTP_METHODS, _load

_SEGMENT_RE = re.compile(r"^(\{[a-z][A-Za-z0-9]*\}|[a-z0-9]+(-[a-z0-9]+)*)$")


def _fallback_lint(doc: dict[str, Any]) -> list[dict[str, Any]]:
    findings = []
    paths = doc.get("paths") or {}
    for route, item in paths.items():
        if not isinstance(item, dict):
            continue
        for segment in (s for s in route.split("/") if s):
            if not _SEGMENT_RE.match(segment):
                findings.append({
                    "location": f"$.paths.{route}", "rule": "path-kebab-case",
                    "severity": "warn",
                    "message": f"path segment {segment!r} should be kebab-case or {{param}}",
                })
        for method, op in item.items():
            if not (isinstance(method, str) and method.lower() in _HTTP_METHODS
                    and isinstance(op, dict)):
                continue
            loc = f"$.paths.{route}.{method.lower()}"
            if not op.get("summary") and not op.get("description"):
                findings.append({"location": loc, "rule": "operation-description",
                                 "severity": "warn",
                                 "message": "operation should have a summary or description"})
            if not op.get("operationId"):
                findings.append({"location": loc, "rule": "operation-operationId",
                                 "severity": "info",
                                 "message": "operation should define an operationId"})
            for param in op.get("parameters") or []:
                if isinstance(param, dict) and not param.get("description"):
                    findings.append({
                        "location": f"{loc}.parameters", "rule": "parameter-description",
                        "severity": "warn",
                        "message": f"parameter {param.get('name', '?')!r} lacks a description",
                    })
    return findings


def lint(spec: Any = None, path: str | None = None, content: str | None = None,
         **kwargs: Any) -> dict[str, Any]:
    """Lint an OpenAPI spec for style issues."""
    if shutil.which("spectral") and path:
        import json

        proc = subprocess.run(["spectral", "lint", "-f", "json", str(path)],
                              capture_output=True, text=True, timeout=300)
        data = json.loads(proc.stdout or "[]")
        findings = [{
            "location": ".".join(str(p) for p in f.get("path", [])),
            "rule": f.get("code", ""), "message": f.get("message", ""),
            "severity": {0: "error", 1: "warn", 2: "info"}.get(f.get("severity", 2), "info"),
        } for f in data]
        engine = "spectral"
        n_paths = 0
    else:
        doc = _load(spec, path, content)
        findings = _fallback_lint(doc)
        engine = "fallback"
        n_paths = len(doc.get("paths") or {})
    return {"status": "ok", "engine": engine, "n_paths": n_paths,
            "n_findings": len(findings), "findings": findings}


def report(spec: Any = None, path: str | None = None, content: str | None = None,
           **kwargs: Any) -> dict[str, Any]:
    """Findings grouped by severity and rule."""
    res = lint(spec, path, content)
    by_sev: dict[str, int] = {}
    by_rule: dict[str, int] = {}
    for f in res["findings"]:
        by_sev[f["severity"]] = by_sev.get(f["severity"], 0) + 1
        by_rule[f["rule"]] = by_rule.get(f["rule"], 0) + 1
    return {"status": "ok", "n_findings": res["n_findings"],
            "by_severity": by_sev, "by_rule": by_rule}


run = skill_run({"lint": lint, "report": report})
register_skill("spectral", run)
