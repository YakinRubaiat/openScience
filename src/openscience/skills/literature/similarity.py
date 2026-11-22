"""semantic_similarity skill: TF-IDF cosine similarity between documents."""

from __future__ import annotations

from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap


def tfidf_cosine(**kwargs: Any) -> dict[str, Any]:
    """Cosine similarity of a query against documents (TF-IDF, pure)."""
    kw = unwrap(kwargs)
    query = kw.get("query") or ""
    docs = kw.get("documents") or kw.get("docs") or []
    if not query or not docs:
        return result(scores=[])
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    vec = TfidfVectorizer(stop_words="english")
    X = vec.fit_transform([query] + list(docs))
    sims = cosine_similarity(X[0:1], X[1:]).ravel()
    return result(scores=[round(float(s), 6) for s in sims])


def top_k_similar(**kwargs: Any) -> dict[str, Any]:
    """Return top-k most similar documents to a query (pure)."""
    kw = unwrap(kwargs)
    k = int(kw.get("k", 5))
    docs = kw.get("documents") or kw.get("docs") or []
    scores = tfidf_cosine(query=kw.get("query") or "", documents=docs)["scores"]
    ranked = sorted(enumerate(scores), key=lambda t: t[1], reverse=True)[:k]
    return result(
        top=[{"index": i, "document": docs[i], "score": s} for i, s in ranked if s > 0]
    )


_OPS = {"tfidf_cosine": tfidf_cosine, "top_k_similar": top_k_similar}


def run(operation: str = "run", **kwargs: Any) -> dict[str, Any]:
    """Dispatch to an operation; ``run`` defaults to ``tfidf_cosine``."""
    op = _OPS.get(operation) or _OPS["tfidf_cosine"]
    if operation not in _OPS and operation != "run":
        raise ValueError(f"Unknown operation {operation!r}. Available: {sorted(_OPS)}")
    return op(**kwargs)


register_skill("semantic_similarity", run)
