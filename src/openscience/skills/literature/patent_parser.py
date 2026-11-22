"""patent_parser skill: extract fields, claims and citations from patent JSON."""

from __future__ import annotations

from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap


def parse(**kwargs: Any) -> dict[str, Any]:
    """Parse a patent JSON dict into standard flat fields (pure)."""
    patent = unwrap(kwargs).get("patent") or unwrap(kwargs).get("json") or {}
    fields = {
        "patent_id": patent.get("publication_number") or patent.get("id") or "",
        "title": patent.get("title") or "",
        "assignee": patent.get("assignee") or "",
        "inventors": patent.get("inventors") or [],
        "priority_date": patent.get("priority_date") or "",
        "filing_date": patent.get("filing_date") or "",
        "grant_date": patent.get("grant_date") or "",
        "abstract": patent.get("abstract") or "",
        "n_claims": len(patent.get("claims") or []),
        "n_citations": len(patent.get("citations") or []),
    }
    return result(fields=fields)


def claims_extract(**kwargs: Any) -> dict[str, Any]:
    """Return the claims list from a patent JSON dict (pure)."""
    patent = unwrap(kwargs).get("patent") or {}
    claims = patent.get("claims") or []
    return result(claims=claims, count=len(claims))


def citations_extract(**kwargs: Any) -> dict[str, Any]:
    """Return the citation list from a patent JSON dict (pure)."""
    patent = unwrap(kwargs).get("patent") or {}
    citations = patent.get("citations") or []
    return result(citations=citations, count=len(citations))


_OPS = {
    "parse": parse,
    "claims_extract": claims_extract,
    "citations_extract": citations_extract,
}


def run(operation: str = "run", **kwargs: Any) -> dict[str, Any]:
    """Dispatch to an operation; ``run`` defaults to ``parse``."""
    op = _OPS.get(operation) or _OPS["parse"]
    if operation not in _OPS and operation != "run":
        raise ValueError(f"Unknown operation {operation!r}. Available: {sorted(_OPS)}")
    return op(**kwargs)


register_skill("patent_parser", run)
