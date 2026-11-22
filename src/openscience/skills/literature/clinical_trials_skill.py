"""clinicaltrials_api skill: search ClinicalTrials.gov v2 and summarize."""

from __future__ import annotations

from collections import Counter
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap


def search(**kwargs: Any) -> dict[str, Any]:
    """Search ClinicalTrials.gov (network). Returns parsed studies."""
    kw = unwrap(kwargs)
    from openscience.connectors.papers import clinicaltrials

    resp = clinicaltrials.search(
        query=kw.get("query") or "", page_size=int(kw.get("page_size", 10))
    )
    studies = [clinicaltrials.parse_study(s) for s in resp.get("studies") or []]
    return result(studies=studies, count=len(studies))


def parse_only(**kwargs: Any) -> dict[str, Any]:
    """Parse a provided study JSON dict (pure, no network)."""
    kw = unwrap(kwargs)
    from openscience.connectors.papers import clinicaltrials

    study = kw.get("study") or kw.get("json") or {}
    return result(study=clinicaltrials.parse_study(study))


def summarize(**kwargs: Any) -> dict[str, Any]:
    """Count provided parsed studies by phase and status (pure)."""
    studies = unwrap(kwargs).get("studies") or []
    by_phase = Counter(s.get("phase") or "Unknown" for s in studies)
    by_status = Counter(s.get("status") or "Unknown" for s in studies)
    return result(
        count=len(studies),
        by_phase=dict(by_phase),
        by_status=dict(by_status),
    )


_OPS = {"search": search, "parse_only": parse_only, "summarize": summarize}


def run(operation: str = "run", **kwargs: Any) -> dict[str, Any]:
    """Dispatch to an operation; ``run`` defaults to ``search``."""
    op = _OPS.get(operation) or _OPS["search"]
    if operation not in _OPS and operation != "run":
        raise ValueError(f"Unknown operation {operation!r}. Available: {sorted(_OPS)}")
    return op(**kwargs)


register_skill("clinicaltrials_api", run)
