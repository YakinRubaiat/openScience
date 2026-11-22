"""safety skill: check requirement pins against an embedded CVE map.

Pure-python; parses ``requirements.txt``-style content and flags packages
pinned below a version known to fix a vulnerability.

Operations: ``check``, ``parse_requirements``.
"""

from __future__ import annotations

import re
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run

# name -> (min safe version, advisory id, summary). Demo map, not exhaustive.
VULN_MAP: dict[str, tuple[str, str, str]] = {
    "flask": ("2.3.0", "CVE-2023-30861", "flask<2.3.0 session cookie parsing flaw"),
    "requests": ("2.31.0", "CVE-2023-32681", "requests<2.31.0 proxy-authorization leak"),
    "pillow": ("10.0.0", "CVE-2023-44271", "pillow<10.0.0 denial of service"),
    "django": ("4.2.0", "CVE-2023-31047", "django<4.2.0 potential SQL injection"),
    "urllib3": ("2.0.0", "CVE-2023-43804", "urllib3<2.0.0 cookie request-header leak"),
    "werkzeug": ("2.3.0", "CVE-2023-25577", "werkzeug<2.3.0 resource exhaustion"),
    "cryptography": ("41.0.0", "CVE-2023-23931", "cryptography<41.0.0 cipher update flaw"),
    "numpy": ("1.22.0", "CVE-2021-41495", "numpy<1.22.0 buffer over-read"),
}

_REQ_RE = re.compile(r"^\s*([A-Za-z0-9_.\-]+)\s*(==|>=|<=|~=|>|<)?\s*([0-9][A-Za-z0-9.\*]*)?")


def _parse_version(text: str) -> tuple[int, ...]:
    parts = []
    for chunk in text.split("."):
        m = re.match(r"\d+", chunk)
        parts.append(int(m.group()) if m else 0)
    return tuple(parts)


def parse_requirements(content: str, **kwargs: Any) -> dict[str, Any]:
    """Parse requirements.txt content into name/spec entries."""
    reqs = []
    for line in content.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith(("-", "git+", "http")):
            continue
        m = _REQ_RE.match(line)
        if not m:
            continue
        name, op, version = m.groups()
        reqs.append({"name": name.lower(), "operator": op or "", "version": version or ""})
    return {"status": "ok", "n_requirements": len(reqs), "requirements": reqs}


def check(content: str | None = None, path: str | None = None, **kwargs: Any) -> dict[str, Any]:
    """Flag requirement pins below versions known to fix vulnerabilities.

    Provide requirements ``content`` directly or a ``path`` to a file.
    """
    if content is None:
        if path is None:
            raise ValueError("Provide requirements 'content' or a 'path' to a file")
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
    reqs = parse_requirements(content)["requirements"]
    findings = []
    for req in reqs:
        info = VULN_MAP.get(req["name"])
        if not info or not req["version"] or req["operator"] not in ("==", "<=", "<"):
            continue
        safe, cve, summary = info
        if _parse_version(req["version"]) < _parse_version(safe):
            findings.append({
                "package": req["name"],
                "installed_spec": f"{req['operator']}{req['version']}",
                "min_safe_version": safe,
                "advisory": cve,
                "summary": summary,
            })
    return {
        "status": "ok",
        "n_requirements": len(reqs),
        "n_vulnerable": len(findings),
        "vulnerabilities": findings,
    }


run = skill_run({"check": check, "parse_requirements": parse_requirements})
register_skill("safety", run)
