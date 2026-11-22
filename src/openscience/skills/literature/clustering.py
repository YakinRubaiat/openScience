"""paper_clustering skill: TF-IDF + KMeans clustering of documents (sklearn)."""

from __future__ import annotations

from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap


def tfidf_kmeans(**kwargs: Any) -> dict[str, Any]:
    """Cluster documents with TF-IDF + KMeans.

    Returns cluster labels (one per doc) and sizes.
    """
    kw = unwrap(kwargs)
    docs = kw.get("documents") or kw.get("docs") or []
    n_clusters = min(int(kw.get("n_clusters", 2)), max(len(docs), 1))
    if len(docs) < n_clusters or not docs:
        return result(labels=[], sizes={}, n_clusters=0)
    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import TfidfVectorizer

    vec = TfidfVectorizer(stop_words="english")
    X = vec.fit_transform(docs)
    km = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
    labels = km.fit_predict(X)
    sizes = {str(k): int((labels == k).sum()) for k in sorted(set(labels.tolist()))}
    return result(labels=[int(x) for x in labels], sizes=sizes, n_clusters=n_clusters)


def summarize_clusters(**kwargs: Any) -> dict[str, Any]:
    """Top TF-IDF terms per cluster for the same docs+labels (pure-ish)."""
    kw = unwrap(kwargs)
    docs = kw.get("documents") or kw.get("docs") or []
    labels = kw.get("labels") or []
    top_n = int(kw.get("top_n", 5))
    if not docs or len(docs) != len(labels):
        return result(clusters={})
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer

    vec = TfidfVectorizer(stop_words="english")
    X = vec.fit_transform(docs)
    terms = vec.get_feature_names_out()
    clusters: dict[str, list[str]] = {}
    for k in sorted(set(labels)):
        idx = [i for i, l in enumerate(labels) if l == k]
        mean_tfidf = np.asarray(X[idx].mean(axis=0)).ravel()
        top_idx = mean_tfidf.argsort()[::-1][:top_n]
        clusters[str(k)] = [str(terms[i]) for i in top_idx if mean_tfidf[i] > 0]
    return result(clusters=clusters)


_OPS = {"tfidf_kmeans": tfidf_kmeans, "summarize_clusters": summarize_clusters}


def run(operation: str = "run", **kwargs: Any) -> dict[str, Any]:
    """Dispatch to an operation; ``run`` defaults to ``tfidf_kmeans``."""
    op = _OPS.get(operation) or _OPS["tfidf_kmeans"]
    if operation not in _OPS and operation != "run":
        raise ValueError(f"Unknown operation {operation!r}. Available: {sorted(_OPS)}")
    return op(**kwargs)


register_skill("paper_clustering", run)
