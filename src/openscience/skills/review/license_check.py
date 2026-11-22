"""license_checker skill: classify dependency licenses into risk buckets.

Buckets: permissive, copyleft (strong + weak), proprietary, unknown.

Operations: ``classify``, ``sbom_summary``, ``flag_copyleft``.
"""

from __future__ import annotations

from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run

_STRONG_COPYLEFT = {"GPL-2.0", "GPL-3.0", "AGPL-3.0", "SSPL-1.0"}
_WEAK_COPYLEFT = {"LGPL-2.1", "LGPL-3.0", "MPL-2.0", "EPL-1.0", "EPL-2.0", "EUPL-1.2", "CDDL-1.0"}
_PERMISSIVE = {
    "MIT", "MIT-0", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0", "ISC",
    "Zlib", "Unlicense", "CC0-1.0", "PSF-2.0", "Python-2.0", "0BSD",
    "BSL-1.0", "PostgreSQL", "WTFPL",
}
_PROPRIETARY_HINTS = ("proprietary", "commercial", "all rights reserved",
                      "licenseRef", "custom", "confidential")


def _normalize(license_text: str) -> str:
    text = (license_text or "").strip()
    if not text:
        return ""
    upper = text.upper().replace("ONLY", "").replace("OR LATER", "+").strip()
    upper = upper.replace("LICENSE", "").replace(" ", "-").strip("-")
    return upper


def classify_one(license_text: str) -> str:
    """Classify one license string into a bucket name."""
    norm = _normalize(license_text)
    if not norm:
        return "unknown"
    for known in _STRONG_COPYLEFT | _WEAK_COPYLEFT | _PERMISSIVE:
        if norm in (known.upper(), known.upper() + "+"):
            if known in _STRONG_COPYLEFT:
                return "copyleft"
            if known in _WEAK_COPYLEFT:
                return "copyleft"
            return "permissive"
    if norm.startswith(("GPL", "AGPL")):
        return "copyleft"
    if any(h.lower() in license_text.lower() for h in _PROPRIETARY_HINTS):
        return "proprietary"
    return "unknown"


def classify(licenses: dict | None = None, package: str | None = None,
             license: str | None = None, **kwargs: Any) -> dict[str, Any]:
    """Bucket a name->license mapping (or a single package/license)."""
    if licenses is None:
        if package is None:
            raise ValueError("Provide 'licenses' mapping or 'package'+'license'")
        licenses = {package: license or ""}
    buckets: dict[str, list[str]] = {"permissive": [], "copyleft": [],
                                     "proprietary": [], "unknown": []}
    detail = []
    for name, lic in licenses.items():
        bucket = classify_one(str(lic or ""))
        buckets[bucket].append(name)
        detail.append({"package": name, "license": lic, "bucket": bucket})
    return {"status": "ok", "n_packages": len(licenses),
            "buckets": buckets, "detail": detail}


def sbom_summary(licenses: dict, **kwargs: Any) -> dict[str, Any]:
    """Counts per bucket for a name->license mapping."""
    res = classify(licenses)
    counts = {k: len(v) for k, v in res["buckets"].items()}
    return {"status": "ok", "n_packages": res["n_packages"], "counts": counts}


def flag_copyleft(licenses: dict, include_weak: bool = True, **kwargs: Any) -> dict[str, Any]:
    """List copyleft-licensed packages that may need review."""
    res = classify(licenses)
    flagged = [d for d in res["detail"] if d["bucket"] == "copyleft"]
    if not include_weak:
        flagged = [d for d in flagged if str(d["license"]).upper().startswith(("GPL", "AGPL"))]
    return {"status": "ok", "n_flagged": len(flagged),
            "flagged": [{"package": d["package"], "license": d["license"]} for d in flagged]}


run = skill_run({"classify": classify, "sbom_summary": sbom_summary,
                 "flag_copyleft": flag_copyleft})
register_skill("license_checker", run)
