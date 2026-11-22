"""fact_verification skill: crude rule-based claim-vs-abstract checks (pure)."""

from __future__ import annotations

import re
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap

_NEGATIONS = ("no ", "not ", "never", "none ", "without", "lack", "absence", "fail")
_STOPWORDS = frozenset(
    "the a an and or of in on to is are was were be been for with by as at from "
    "this that these those it its their we our they he she".split()
)


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOPWORDS}


def claim_vs_abstract_rules(**kwargs: Any) -> dict[str, Any]:
    """Score a claim against one abstract (pure, crude heuristics).

    ``score`` = Jaccard overlap of content tokens. ``contradicted`` is True
    when the abstract contains negation markers absent in the claim.
    """
    kw = unwrap(kwargs)
    claim = (kw.get("claim") or "").lower()
    abstract = (kw.get("abstract") or "").lower()
    ctoks, atoks = _tokens(claim), _tokens(abstract)
    union = ctoks | atoks
    overlap = len(ctoks & atoks) / len(union) if union else 0.0
    claim_neg = any(m in claim for m in _NEGATIONS)
    abstract_neg = any(m in abstract for m in _NEGATIONS)
    contradicted = bool(abstract_neg and not claim_neg and overlap >= 0.1)
    verdict = "contradicted" if contradicted else ("supported" if overlap >= 0.3 else "unclear")
    return result(
        verdict=verdict,
        score=round(overlap, 4),
        contradicted=contradicted,
        claim_negation=claim_neg,
        abstract_negation=abstract_neg,
    )


def report_table(**kwargs: Any) -> dict[str, Any]:
    """Score a claim against many abstracts; returns one row per paper (pure)."""
    kw = unwrap(kwargs)
    claim = kw.get("claim") or ""
    papers = kw.get("papers") or []
    rows = []
    for p in papers:
        r = claim_vs_abstract_rules(claim=claim, abstract=p.get("abstract") or "")
        rows.append(
            {
                "paper": p.get("title", "")[:60],
                "verdict": r["verdict"],
                "score": r["score"],
            }
        )
    return result(rows=rows, count=len(rows))


_OPS = {
    "claim_vs_abstract_rules": claim_vs_abstract_rules,
    "report_table": report_table,
}


def run(operation: str = "run", **kwargs: Any) -> dict[str, Any]:
    """Dispatch to an operation; ``run`` defaults to ``claim_vs_abstract_rules``."""
    op = _OPS.get(operation) or _OPS["claim_vs_abstract_rules"]
    if operation not in _OPS and operation != "run":
        raise ValueError(f"Unknown operation {operation!r}. Available: {sorted(_OPS)}")
    return op(**kwargs)


register_skill("fact_verification", run)
