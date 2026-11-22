"""trend_detection skill: year counts, emerging terms (chi2), growth rates."""

from __future__ import annotations

from collections import Counter
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap


def by_year_counts(**kwargs: Any) -> dict[str, Any]:
    """Count papers per year (pure)."""
    papers = unwrap(kwargs).get("papers") or []
    counts = Counter(p.get("year") for p in papers if p.get("year"))
    return result(counts={str(y): c for y, c in sorted(counts.items())})


def emerging_terms(**kwargs: Any) -> dict[str, Any]:
    """Rank terms by chi2 of recent-vs-old document frequencies (pure).

    ``papers`` are dicts with ``year`` and ``terms`` (list of str).
    ``split_year`` divides old (< split) from recent (>= split).
    """
    kw = unwrap(kwargs)
    papers = kw.get("papers") or []
    split = int(kw.get("split_year", 2020))
    top_n = int(kw.get("top_n", 10))
    old_docs = [p for p in papers if (p.get("year") or 0) < split]
    new_docs = [p for p in papers if (p.get("year") or 0) >= split]
    if not old_docs or not new_docs:
        return result(terms=[])
    old_counts: Counter[str] = Counter(t for p in old_docs for t in set(p.get("terms") or []))
    new_counts: Counter[str] = Counter(t for p in new_docs for t in set(p.get("terms") or []))
    n_old, n_new = len(old_docs), len(new_docs)
    rows = []
    for term in set(old_counts) | set(new_counts):
        a, b = new_counts[term], n_new - new_counts[term]
        c, d = old_counts[term], n_old - old_counts[term]
        total = a + b + c + d
        exp_a = (a + b) * (a + c) / total
        if exp_a == 0:
            continue
        chi2 = (a - exp_a) ** 2 / exp_a
        # only report enriched in recent period
        if a / n_new > c / n_old:
            rows.append({"term": term, "chi2": round(chi2, 4), "recent": a, "old": c})
    rows.sort(key=lambda r: r["chi2"], reverse=True)
    return result(terms=rows[:top_n])


def growth_rate(**kwargs: Any) -> dict[str, Any]:
    """Per-year CAGR-style growth rates between first and last year (pure).

    Accepts ``counts`` dict {year: n} or ``papers`` list.
    """
    kw = unwrap(kwargs)
    counts = kw.get("counts") or {}
    if not counts and kw.get("papers"):
        c = Counter(p.get("year") for p in kw["papers"] if p.get("year"))
        counts = {str(y): n for y, n in c.items()}
    counts = {int(y): int(n) for y, n in counts.items()}
    if len(counts) < 2:
        return result(growth_rate=None)
    years = sorted(counts)
    first, last = years[0], years[-1]
    n_first, n_last = counts[first], counts[last]
    if n_first <= 0 or last == first:
        return result(growth_rate=None)
    rate = (n_last / n_first) ** (1 / (last - first)) - 1
    return result(
        growth_rate=round(rate, 4),
        first_year=first, last_year=last, first_count=n_first, last_count=n_last,
    )


_OPS = {
    "by_year_counts": by_year_counts,
    "emerging_terms": emerging_terms,
    "growth_rate": growth_rate,
}


def run(operation: str = "run", **kwargs: Any) -> dict[str, Any]:
    """Dispatch to an operation; ``run`` defaults to ``by_year_counts``."""
    op = _OPS.get(operation) or _OPS["by_year_counts"]
    if operation not in _OPS and operation != "run":
        raise ValueError(f"Unknown operation {operation!r}. Available: {sorted(_OPS)}")
    return op(**kwargs)


register_skill("trend_detection", run)
