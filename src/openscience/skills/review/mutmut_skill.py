"""mutmut skill: mutation testing wrapper.

``run`` shells out to the mutmut CLI when installed (clear RuntimeError
otherwise). ``parse_results`` reads ``mutmut results`` output, the mutmut
cache (``.mutmut-cache``), or a JUnit XML file. ``survival_rate`` computes
the percentage of mutants that survived.

Operations: ``run``, ``parse_results``, ``survival_rate``.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run


def run(path: str = ".", paths_to_mutate: str | None = None,
        extra_args: list | None = None, **kwargs: Any) -> dict[str, Any]:
    """Run mutation testing with the mutmut CLI."""
    if shutil.which("mutmut") is None:
        raise RuntimeError("install with: pip install mutmut")
    cmd = ["mutmut", "run", *(extra_args or [])]
    if paths_to_mutate:
        cmd += [f"--paths-to-mutate={paths_to_mutate}"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=3600, cwd=path)
    return {"status": "ok" if proc.returncode == 0 else "finished-with-kills",
            "returncode": proc.returncode,
            "tail": "\n".join((proc.stdout.splitlines() or [""])[-20:])}


def _parse_text_results(text: str) -> dict[str, int]:
    counts = {"killed": 0, "survived": 0, "timeout": 0, "suspicious": 0, "no_tests": 0}
    pattern_map = {
        "killed": r"(?:killed|🎉)\s*[:=]?\s*(\d+)",
        "survived": r"(?:survived|🙁)\s*[:=]?\s*(\d+)",
        "timeout": r"(?:timeout|⏰)\s*[:=]?\s*(\d+)",
        "suspicious": r"(?:suspicious|🤔)\s*[:=]?\s*(\d+)",
        "no_tests": r"(?:no tests|untested|skipped)\s*[:=]?\s*(\d+)",
    }
    for key, pat in pattern_map.items():
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            counts[key] = int(m.group(1))
    # fall back to tallying bullet lines like "1234: survived"
    if not any(counts.values()):
        counts["killed"] = len(re.findall(r":\s*killed\b", text))
        counts["survived"] = len(re.findall(r":\s*survived\b", text))
    return counts


def parse_results(path: str, **kwargs: Any) -> dict[str, Any]:
    """Parse mutmut results from a JUnit XML, .mutmut-cache, or text file."""
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="replace")
    counts: dict[str, int]
    engine = "text"
    if text.lstrip().startswith("<"):
        root = ET.fromstring(text)
        if root.tag in ("testsuite", "testsuites"):
            total = failures = 0
            for ts in root.iter("testsuite"):
                total += int(ts.get("tests", 0))
                failures += int(ts.get("failures", 0)) + int(ts.get("errors", 0))
            # mutmut junit: failures are surviving mutants
            counts = {"killed": total - failures, "survived": failures,
                      "timeout": 0, "suspicious": 0, "no_tests": 0}
            engine = "junit-xml"
        else:
            counts = _parse_text_results(text)
    else:
        try:
            data = json.loads(text)
            if isinstance(data, dict) and any(k in data for k in ("killed", "survived")):
                counts = {k: int(data.get(k, 0)) for k in
                          ("killed", "survived", "timeout", "suspicious", "no_tests")}
                engine = "json"
            else:
                counts = _parse_text_results(text)
        except json.JSONDecodeError:
            counts = _parse_text_results(text)
    total = sum(counts.values())
    return {"status": "ok", "engine": engine, "counts": counts, "total_mutants": total}


def survival_rate(path: str, **kwargs: Any) -> dict[str, Any]:
    """Percent of mutants that survived (lower is better)."""
    parsed = parse_results(path)
    scored = parsed["counts"]["killed"] + parsed["counts"]["survived"]
    rate = round(100.0 * parsed["counts"]["survived"] / scored, 2) if scored else 0.0
    return {"status": "ok", "survival_rate_percent": rate,
            "killed": parsed["counts"]["killed"],
            "survived": parsed["counts"]["survived"]}


run = skill_run({"run": run, "parse_results": parse_results,
                 "survival_rate": survival_rate})
register_skill("mutmut", run)
