"""trivy skill: vulnerability scanner wrapper.

``scan`` shells out to the trivy CLI (clear RuntimeError when absent).
``parse_json`` summarises trivy JSON output into vulnerability counts by
severity — works offline on any saved trivy report.

Operations: ``scan``, ``parse_json``.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run

_SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN")


def scan(target: str, scan_type: str = "fs", timeout: int = 900, **kwargs: Any) -> dict[str, Any]:
    """Run ``trivy <scan_type> --format json <target>`` and parse the result."""
    if shutil.which("trivy") is None:
        raise RuntimeError("install with: brew install trivy  # or from aquasecurity releases")
    if scan_type not in ("fs", "image", "config", "repo"):
        raise ValueError("scan_type must be one of fs/image/config/repo")
    proc = subprocess.run(["trivy", scan_type, "--format", "json", "--quiet", target],
                          capture_output=True, text=True, timeout=timeout)
    if not proc.stdout.strip():
        raise RuntimeError(f"trivy failed: {proc.stderr.strip()[:400]}")
    return parse_json(report=proc.stdout)


def parse_json(report: str | None = None, path: str | None = None,
               **kwargs: Any) -> dict[str, Any]:
    """Vulnerability counts by severity from trivy JSON (text or file path)."""
    if report is None:
        if path is None:
            raise ValueError("Provide trivy 'report' JSON text or a 'path'")
        report = Path(path).read_text(encoding="utf-8")
    data = json.loads(report)
    counts = {s: 0 for s in _SEVERITIES}
    detail = []
    results = data.get("Results") or []
    for res in results:
        for vuln in res.get("Vulnerabilities") or []:
            sev = str(vuln.get("Severity", "UNKNOWN")).upper()
            counts[sev] = counts.get(sev, 0) + 1
            detail.append({
                "id": vuln.get("VulnerabilityID", ""),
                "pkg": vuln.get("PkgName", ""),
                "severity": sev,
                "fixed": vuln.get("FixedVersion", ""),
                "target": res.get("Target", ""),
            })
    return {"status": "ok", "n_vulnerabilities": len(detail),
            "by_severity": counts, "vulnerabilities": detail}


run = skill_run({"scan": scan, "parse_json": parse_json})
register_skill("trivy", run)
