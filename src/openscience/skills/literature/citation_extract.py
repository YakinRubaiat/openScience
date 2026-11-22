"""citation_extraction skill: regex DOI/PMID/author-year extraction (pure)."""

from __future__ import annotations

import re
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap

_DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b")
_PMID_RE = re.compile(r"\bPMID[:\s]*(\d{6,9})\b", re.IGNORECASE)
_AUTH_YEAR_RE = re.compile(r"\(([A-Z][A-Za-z\-]+(?:\s+et\s+al\.)?(?:\s+and\s+[A-Z][A-Za-z\-]+)?),?\s+(\d{4}[a-z]?)\)")


def from_text(**kwargs: Any) -> dict[str, Any]:
    """Extract DOIs, PMIDs and author-year citations from free text (pure)."""
    text = unwrap(kwargs).get("text") or ""
    dois = sorted(set(_DOI_RE.findall(text)))
    pmids = sorted({m.group(1) for m in _PMID_RE.finditer(text)})
    author_years = [
        {"author": m.group(1), "year": m.group(2)} for m in _AUTH_YEAR_RE.finditer(text)
    ]
    return result(dois=dois, pmids=pmids, author_years=author_years)


def to_reference_dict(**kwargs: Any) -> dict[str, Any]:
    """Convert a citation dict (doi/pmid/authors/year/title) to a reference."""
    kw = unwrap(kwargs)
    ref = {
        "doi": kw.get("doi") or "",
        "pmid": kw.get("pmid") or "",
        "title": kw.get("title") or "",
        "authors": kw.get("authors") or [],
        "year": kw.get("year"),
        "journal": kw.get("journal") or "",
    }
    if kw.get("author"):
        ref["authors"] = [kw["author"]]
    return result(reference=ref)


_OPS = {"from_text": from_text, "to_reference_dict": to_reference_dict}


def run(operation: str = "run", **kwargs: Any) -> dict[str, Any]:
    """Dispatch to an operation; ``run`` defaults to ``from_text``."""
    op = _OPS.get(operation) or _OPS["from_text"]
    if operation not in _OPS and operation != "run":
        raise ValueError(f"Unknown operation {operation!r}. Available: {sorted(_OPS)}")
    return op(**kwargs)


register_skill("citation_extraction", run)
