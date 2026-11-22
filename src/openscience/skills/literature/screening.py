"""screening_automation skill: keyword screening, deduplication, sampling."""

from __future__ import annotations

import hashlib
import random
import re
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap


def keyword_screen(**kwargs: Any) -> dict[str, Any]:
    """Score papers by include/exclude regex hits on title+abstract (pure).

    Decision: any exclude hit -> 'exclude'; >=1 include hit -> 'include';
    otherwise 'uncertain'.
    """
    kw = unwrap(kwargs)
    papers = kw.get("papers") or []
    include = [re.compile(p, re.I) for p in (kw.get("include_patterns") or [])]
    exclude = [re.compile(p, re.I) for p in (kw.get("exclude_patterns") or [])]
    screened = []
    for p in papers:
        text = f"{p.get('title', '')} {p.get('abstract', '')}"
        inc = sum(len(rx.findall(text)) for rx in include)
        exc = sum(len(rx.findall(text)) for rx in exclude)
        decision = "exclude" if exc else ("include" if inc else "uncertain")
        screened.append(
            {
                "title": p.get("title", "")[:80],
                "include_score": inc,
                "exclude_score": exc,
                "decision": decision,
            }
        )
    return result(screened=screened, count=len(screened))


def _paper_key(p: dict[str, Any]) -> str:
    doi = (p.get("doi") or "").strip().lower()
    if doi:
        return f"doi:{doi}"
    title = " ".join((p.get("title") or "").lower().split())
    return f"title:{hashlib.md5(title.encode()).hexdigest()}"


def dedupe(**kwargs: Any) -> dict[str, Any]:
    """Remove duplicate papers by DOI (fallback: normalized title) (pure)."""
    papers = unwrap(kwargs).get("papers") or []
    seen: dict[str, dict] = {}
    for p in papers:
        seen.setdefault(_paper_key(p), p)
    return result(papers=list(seen.values()), n_duplicates=len(papers) - len(seen))


def sample_for_review(**kwargs: Any) -> dict[str, Any]:
    """Deterministically sample n papers for manual review (pure)."""
    kw = unwrap(kwargs)
    papers = kw.get("papers") or []
    n = int(kw.get("n", 10))
    rng = random.Random(int(kw.get("seed", 42)))
    sample = rng.sample(papers, min(n, len(papers)))
    return result(sample=sample, count=len(sample))


_OPS = {
    "keyword_screen": keyword_screen,
    "dedupe": dedupe,
    "sample_for_review": sample_for_review,
}


def run(operation: str = "run", **kwargs: Any) -> dict[str, Any]:
    """Dispatch to an operation; ``run`` defaults to ``keyword_screen``."""
    op = _OPS.get(operation) or _OPS["keyword_screen"]
    if operation not in _OPS and operation != "run":
        raise ValueError(f"Unknown operation {operation!r}. Available: {sorted(_OPS)}")
    return op(**kwargs)


register_skill("screening_automation", run)
