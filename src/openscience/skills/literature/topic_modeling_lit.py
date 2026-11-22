"""topic_modeling_lit skill: NMF topics over a small document set (sklearn)."""

from __future__ import annotations

from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap


def _fit_nmf(docs: list[str], n_topics: int, top_n: int):
    from sklearn.decomposition import NMF
    from sklearn.feature_extraction.text import TfidfVectorizer

    vec = TfidfVectorizer(stop_words="english")
    X = vec.fit_transform(docs)
    n_topics = max(1, min(n_topics, X.shape[1], len(docs)))
    model = NMF(n_components=n_topics, random_state=42, init="nndsvda", max_iter=200)
    W = model.fit_transform(X)
    return vec, model, W


def nmf_topics(**kwargs: Any) -> dict[str, Any]:
    """Fit NMF; returns topics with their top terms."""
    kw = unwrap(kwargs)
    docs = kw.get("documents") or kw.get("docs") or []
    if not docs:
        return result(topics=[], n_topics=0)
    n_topics = int(kw.get("n_topics", 2))
    top_n = int(kw.get("top_n", 5))
    vec, model, _W = _fit_nmf(docs, n_topics, top_n)
    terms = vec.get_feature_names_out()
    topics = []
    for i, comp in enumerate(model.components_):
        top_idx = comp.argsort()[::-1][:top_n]
        topics.append({"topic": i, "terms": [str(terms[j]) for j in top_idx if comp[j] > 0]})
    return result(topics=topics, n_topics=len(topics))


def top_terms(**kwargs: Any) -> dict[str, Any]:
    """Top TF-IDF terms across the whole corpus (no model fit)."""
    kw = unwrap(kwargs)
    docs = kw.get("documents") or kw.get("docs") or []
    top_n = int(kw.get("top_n", 10))
    if not docs:
        return result(terms=[])
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer

    vec = TfidfVectorizer(stop_words="english")
    X = vec.fit_transform(docs)
    scores = np.asarray(X.sum(axis=0)).ravel()
    terms = vec.get_feature_names_out()
    top_idx = scores.argsort()[::-1][:top_n]
    return result(terms=[str(terms[i]) for i in top_idx if scores[i] > 0])


def doc_topic_matrix(**kwargs: Any) -> dict[str, Any]:
    """Document-topic weights matrix (rows = docs) from a fitted NMF."""
    kw = unwrap(kwargs)
    docs = kw.get("documents") or kw.get("docs") or []
    if not docs:
        return result(matrix=[])
    n_topics = int(kw.get("n_topics", 2))
    _vec, _model, W = _fit_nmf(docs, n_topics, 5)
    return result(matrix=[[round(float(v), 4) for v in row] for row in W])


_OPS = {
    "nmf_topics": nmf_topics,
    "top_terms": top_terms,
    "doc_topic_matrix": doc_topic_matrix,
}


def run(operation: str = "run", **kwargs: Any) -> dict[str, Any]:
    """Dispatch to an operation; ``run`` defaults to ``nmf_topics``."""
    op = _OPS.get(operation) or _OPS["nmf_topics"]
    if operation not in _OPS and operation != "run":
        raise ValueError(f"Unknown operation {operation!r}. Available: {sorted(_OPS)}")
    return op(**kwargs)


register_skill("topic_modeling_lit", run)
