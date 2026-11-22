"""bibliometric_analysis skill: year/journal/author counts and h-index (pure)."""

from __future__ import annotations

from collections import Counter
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap


def counts_by_year(**kwargs: Any) -> dict[str, Any]:
    """Count papers per year from a list of paper dicts (pure)."""
    papers = unwrap(kwargs).get("papers") or []
    counts = Counter(p.get("year") for p in papers if p.get("year"))
    return result(counts_by_year={str(y): c for y, c in sorted(counts.items())})


def top_journals(**kwargs: Any) -> dict[str, Any]:
    """Top-N journals by paper count (pure)."""
    kw = unwrap(kwargs)
    papers = kw.get("papers") or []
    n = int(kw.get("n", 10))
    counts = Counter(
        p.get("journal") or p.get("source") or "" for p in papers
    )
    counts.pop("", None)
    return result(top_journals=[{"journal": j, "count": c} for j, c in counts.most_common(n)])


def top_authors(**kwargs: Any) -> dict[str, Any]:
    """Top-N authors by paper count (pure)."""
    kw = unwrap(kwargs)
    papers = kw.get("papers") or []
    n = int(kw.get("n", 10))
    counts = Counter(a for p in papers for a in (p.get("authors") or []))
    return result(top_authors=[{"author": a, "count": c} for a, c in counts.most_common(n)])


def h_index(**kwargs: Any) -> dict[str, Any]:
    """Compute the h-index from a list of citation counts (pure)."""
    counts = sorted((int(c) for c in unwrap(kwargs).get("citations") or []), reverse=True)
    h = 0
    for i, c in enumerate(counts, start=1):
        if c >= i:
            h = i
        else:
            break
    return result(h_index=h)


_OPS = {
    "counts_by_year": counts_by_year,
    "top_journals": top_journals,
    "top_authors": top_authors,
    "h_index": h_index,
}


def run(operation: str = "run", **kwargs: Any) -> dict[str, Any]:
    """Dispatch to an operation; ``run`` defaults to ``counts_by_year``."""
    op = _OPS.get(operation) or _OPS["counts_by_year"]
    if operation not in _OPS and operation != "run":
        raise ValueError(f"Unknown operation {operation!r}. Available: {sorted(_OPS)}")
    return op(**kwargs)


register_skill("bibliometric_analysis", run)
