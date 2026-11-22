"""Dimensionality reduction skill: PCA, t-SNE, UMAP, and kNN graphs.

Operations
----------
- ``pca``       — sklearn PCA returning scores + explained variance
- ``tsne``      — sklearn t-SNE with a small-sample guard on perplexity
- ``umap``      — UMAP embedding (graceful error if ``umap-learn`` missing)
- ``knn_graph`` — k-nearest-neighbour indices/distances adjacency
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import has_module, optional_import, skill_run, unwrap


def _get_matrix(kw: dict[str, Any]) -> tuple[np.ndarray, list[str]]:
    if "array" in kw:
        X = np.asarray(kw["array"], dtype=float)
        features = [f"x{i}" for i in range(X.shape[1])]
        return X, features
    if "dataframe" in kw:
        df = pd.DataFrame(kw["dataframe"])
    elif "records" in kw:
        df = pd.DataFrame(kw["records"])
    else:
        raise ValueError("Provide 'array', 'dataframe', or 'records'")
    df = df.select_dtypes(include=[np.number])
    return df.to_numpy(dtype=float), [str(c) for c in df.columns]


def pca(**kwargs: Any) -> dict[str, Any]:
    """PCA embedding.

    Parameters: data, ``n_components`` (default min(5, dims)), ``scale``
    (default True).
    """
    decomposition = optional_import("sklearn.decomposition", package="scikit-learn")

    kw = unwrap(kwargs)
    X, features = _get_matrix(kw)
    scale = bool(kw.get("scale", True))

    if scale and X.shape[0] > 0:
        mean = X.mean(axis=0)
        std = X.std(axis=0)
        std[std == 0] = 1.0
        X = (X - mean) / std

    n_samp, n_feat = X.shape
    max_comp = max(1, min(n_feat, n_samp))
    n_components = int(kw.get("n_components", min(5, max_comp)))
    n_components = max(1, min(n_components, max_comp))

    pca_model = decomposition.PCA(n_components=n_components)
    scores = pca_model.fit_transform(X)

    return {
        "n_samples": int(n_samp),
        "n_features": int(n_feat),
        "n_components": int(n_components),
        "explained_variance_ratio": [float(v) for v in pca_model.explained_variance_ratio_],
        "cumulative_explained_variance": [
            float(v) for v in np.cumsum(pca_model.explained_variance_ratio_)
        ],
        "scores": scores.tolist(),
        "components": pca_model.components_.tolist(),
        "feature_names": features,
    }


def tsne(**kwargs: Any) -> dict[str, Any]:
    """t-SNE embedding with a small-sample perplexity guard.

    Parameters: data, ``n_components`` (default 2), ``perplexity`` (default
    30, clamped below to ``max(1, (n-1)/3)``), ``random_state``.
    """
    manifold = optional_import("sklearn.manifold", package="scikit-learn")

    kw = unwrap(kwargs)
    X, _features = _get_matrix(kw)
    n_samples = X.shape[0]
    if n_samples < 3:
        raise ValueError("t-SNE requires at least 3 samples")

    n_components = int(kw.get("n_components", 2))
    perplexity = float(kw.get("perplexity", 30.0))
    max_perp = max(1.0, (n_samples - 1) / 3.0)
    if perplexity > max_perp:
        perplexity = max_perp
    random_state = kw.get("random_state", 0)

    model = manifold.TSNE(
        n_components=n_components,
        perplexity=perplexity,
        random_state=random_state,
        init="pca",
        learning_rate="auto",
    )
    emb = model.fit_transform(X)
    return {
        "n_samples": int(n_samples),
        "n_components": int(n_components),
        "perplexity": float(perplexity),
        "embedding": emb.tolist(),
        "kl_divergence": float(model.kl_divergence_),
    }


def umap(**kwargs: Any) -> dict[str, Any]:
    """UMAP embedding. Requires the ``umap-learn`` package."""
    if not has_module("umap"):
        raise RuntimeError(
            "Skill dependency 'umap' is not installed. "
            "Install it with: pip install umap-learn"
        )
    umap_module = optional_import("umap", package="umap-learn")

    kw = unwrap(kwargs)
    X, _features = _get_matrix(kw)
    n_samples = X.shape[0]
    if n_samples < 3:
        raise ValueError("UMAP requires at least 3 samples")

    n_components = int(kw.get("n_components", 2))
    n_neighbors = int(kw.get("n_neighbors", 15))
    n_neighbors = max(2, min(n_neighbors, n_samples - 1))
    random_state = kw.get("random_state", 0)

    reducer = umap_module.UMAP(
        n_components=n_components,
        n_neighbors=n_neighbors,
        random_state=random_state,
    )
    emb = reducer.fit_transform(X)
    return {
        "n_samples": int(n_samples),
        "n_components": int(n_components),
        "n_neighbors": int(n_neighbors),
        "embedding": np.asarray(emb).tolist(),
    }


def knn_graph(**kwargs: Any) -> dict[str, Any]:
    """k-nearest-neighbour graph: neighbour indices and distances.

    Parameters: data, ``k`` (default 5, clamped to n-1), ``metric``
    (default ``"euclidean"``).
    """
    neighbors = optional_import("sklearn.neighbors", package="scikit-learn")

    kw = unwrap(kwargs)
    X, _features = _get_matrix(kw)
    n_samples = X.shape[0]
    if n_samples < 2:
        raise ValueError("kNN graph requires at least 2 samples")

    k = int(kw.get("k", 5))
    k = max(1, min(k, n_samples - 1))
    metric = kw.get("metric", "euclidean")

    nn = neighbors.NearestNeighbors(n_neighbors=k, metric=metric)
    nn.fit(X)
    distances, indices = nn.kneighbors(X)

    return {
        "n_samples": int(n_samples),
        "k": int(k),
        "metric": str(metric),
        "indices": indices.tolist(),
        "distances": distances.tolist(),
    }


run = skill_run(
    {
        "pca": pca,
        "tsne": tsne,
        "umap": umap,
        "knn_graph": knn_graph,
    }
)

register_skill("dimensionality_reduction", run)
