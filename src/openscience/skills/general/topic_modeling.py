"""topic_modeling skill: extract themes from a corpus of papers.

Uses TF-IDF + NMF when sklearn is available. Falls back to plain term
frequency if not. Also extracts per-year MeSH term counts so the
trend_tracker agent can detect *emerging* themes.
"""

from collections import Counter, defaultdict
from typing import Any


def run(
    operation: str, parameters: dict | None = None, context: dict | None = None, **kwargs
) -> dict:
    if operation != "run":
        raise ValueError(f"Unsupported operation: {operation}")
    parameters = parameters or {}
    papers = parameters.get("papers") or (context or {}).get("papers") or []
    n_topics = int(parameters.get("n_topics", 5))
    n_top_words = int(parameters.get("n_top_words", 10))

    docs = [_paper_to_text(p) for p in papers]
    years = [p.get("year") for p in papers]

    out: dict[str, Any] = {
        "n_papers": len(papers),
        "topics": _tfidf_topics(docs, n_topics=n_topics, n_top_words=n_top_words),
        "mesh_by_year": _mesh_by_year(papers),
        "emerging_mesh": _emerging(papers),
        "yearly_counts": dict(Counter(y for y in years if y)),
    }
    return out


def _paper_to_text(p: dict) -> str:
    parts = [p.get("title") or "", p.get("abstract") or ""]
    parts.extend(p.get("mesh_terms") or [])
    return " ".join(parts)


def _tfidf_topics(docs: list[str], n_topics: int, n_top_words: int) -> list[dict]:
    docs = [d for d in docs if d.strip()]
    if not docs:
        return []
    try:
        from sklearn.decomposition import NMF
        from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

        stop = list(ENGLISH_STOP_WORDS) + [
            "crispr",
            "cas9",
            "cancer",
            "gene",
            "editing",
            "cell",
            "cells",
            "therapy",
            "treatment",
            "tumor",
            "tumour",
            "patient",
            "patients",
            "may",
            "using",
            "based",
            "study",
            "studies",
            "results",
            "however",
            "also",
            "including",
            "used",
            "use",
            "review",
        ]
        n_topics = max(1, min(n_topics, len(docs) - 1))
        vec = TfidfVectorizer(max_features=2000, stop_words=stop, ngram_range=(1, 2), min_df=1)
        X = vec.fit_transform(docs)
        if X.shape[1] < n_topics:
            n_topics = max(1, X.shape[1])
        nmf = NMF(n_components=n_topics, random_state=42, init="nndsvda", max_iter=400)
        nmf.fit_transform(X)
        H = nmf.components_
        feat = vec.get_feature_names_out()
        topics = []
        for i, row in enumerate(H):
            top_idx = row.argsort()[::-1][:n_top_words]
            topics.append(
                {
                    "topic_id": i,
                    "top_words": [feat[j] for j in top_idx],
                    "weight_sum": float(row.sum()),
                }
            )
        return topics
    except Exception:
        # Pure-python fallback: just term frequency
        counts: Counter = Counter()
        for d in docs:
            for tok in d.lower().split():
                if len(tok) > 4 and tok.isalpha():
                    counts[tok] += 1
        return [{"topic_id": 0, "top_words": [w for w, _ in counts.most_common(15)]}]


def _mesh_by_year(papers: list[dict]) -> dict[int, list[tuple[str, int]]]:
    by_year: dict[int, Counter] = defaultdict(Counter)
    for p in papers:
        y = p.get("year")
        if not y:
            continue
        for term in p.get("mesh_terms") or []:
            by_year[y][term.lower()] += 1
    return {y: c.most_common(15) for y, c in sorted(by_year.items())}


def _emerging(papers: list[dict], recent_years: int = 2) -> list[dict]:
    """Simple 'emerging' detector: terms whose frequency share is rising."""
    years = sorted({p.get("year") for p in papers if p.get("year")})
    if len(years) < 2:
        return []
    cutoff = years[-recent_years] if len(years) >= recent_years else years[-1]
    old_counts: Counter = Counter()
    new_counts: Counter = Counter()
    old_total = new_total = 0
    for p in papers:
        y = p.get("year")
        if not y:
            continue
        target = new_counts if y >= cutoff else old_counts
        for term in p.get("mesh_terms") or []:
            target[term.lower()] += 1
            if y >= cutoff:
                new_total += 1
            else:
                old_total += 1
    emerging = []
    for term, new_n in new_counts.items():
        old_n = old_counts.get(term, 0)
        old_share = old_n / max(old_total, 1)
        new_share = new_n / max(new_total, 1)
        if new_share > old_share and new_n >= 2:
            emerging.append(
                {
                    "term": term,
                    "old_share": round(old_share, 4),
                    "new_share": round(new_share, 4),
                    "delta": round(new_share - old_share, 4),
                    "new_count": new_n,
                }
            )
    emerging.sort(key=lambda x: x["delta"], reverse=True)
    return emerging[:20]
