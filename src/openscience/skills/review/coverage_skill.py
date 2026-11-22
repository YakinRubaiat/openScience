"""coverage skill: test coverage measurement and XML parsing.

``run`` uses pytest-cov via subprocess when available (clear RuntimeError
otherwise). ``parse_coverage_xml`` parses Cobertura-style coverage.xml with
the stdlib only. ``line_coverage_percent`` is a convenience percent lookup.

Operations: ``run``, ``parse_coverage_xml``, ``line_coverage_percent``.
"""

from __future__ import annotations

import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run
from openscience.skills.review import _ast_common as ac


def run(path: str = ".", source: str = ".", cov_file: str = "coverage.xml",
        extra_args: list | None = None, **kwargs: Any) -> dict[str, Any]:
    """Run pytest with pytest-cov producing ``cov_file`` and parse it."""
    ac.require_tool("pytest_cov", "pytest-cov")
    cmd = [sys.executable, "-m", "pytest", f"--cov={source}",
           f"--cov-report=xml:{cov_file}", "-q", path, *(extra_args or [])]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    xml_path = Path(cov_file)
    parsed = parse_coverage_xml(str(xml_path)) if xml_path.exists() else None
    return {"status": "ok" if proc.returncode == 0 else "failed",
            "returncode": proc.returncode,
            "coverage": parsed,
            "tail": "\n".join((proc.stdout.splitlines() or [""])[-20:])}


def parse_coverage_xml(path: str, **kwargs: Any) -> dict[str, Any]:
    """Parse a Cobertura coverage.xml: per-file and overall line rates."""
    tree = ET.parse(path)
    root = tree.getroot()
    if root.tag != "coverage":
        raise ValueError(f"Not a coverage.xml file: {path} (root <{root.tag}>)")
    files = []
    for cls in root.iter("class"):
        lines = cls.find("lines")
        hits = valid = 0
        if lines is not None:
            for line in lines.iter("line"):
                valid += 1
                if int(line.get("hits", "0")) > 0:
                    hits += 1
        rate = round(hits / valid, 4) if valid else float(cls.get("line-rate", 0.0))
        files.append({"file": cls.get("filename", ""), "line_rate": rate,
                      "covered": hits, "valid": valid})
    overall_rate = float(root.get("line-rate", 0.0))
    return {"status": "ok", "line_rate": overall_rate,
            "line_coverage_percent": round(overall_rate * 100, 2),
            "branch_rate": float(root.get("branch-rate", 0.0)),
            "n_files": len(files), "files": files}


def line_coverage_percent(path: str, **kwargs: Any) -> dict[str, Any]:
    """Overall line-coverage percent from a coverage.xml file."""
    parsed = parse_coverage_xml(path)
    return {"status": "ok", "line_coverage_percent": parsed["line_coverage_percent"],
            "n_files": parsed["n_files"]}


run = skill_run({"run": run, "parse_coverage_xml": parse_coverage_xml,
                 "line_coverage_percent": line_coverage_percent})
register_skill("coverage", run)
