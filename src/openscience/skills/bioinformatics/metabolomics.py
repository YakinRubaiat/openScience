"""General metabolomics statistics skill.

- ``tics_normalize`` — total-ion-current normalisation (each sample scaled
  so its total intensity matches the median total)
- ``pca_scores``     — PCA scores of log-transformed intensities (sklearn)
- ``plsda_scores``   — PLS-DA scores against a two-class label (sklearn PLS)
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import unwrap

_EPS = 1e-10


def _matrix(data=None, kw=None) -> pd.DataFrame:
    kw = kw or {}
    m = data if data is not None else kw.get("data") or kw.get("intensities")
    if m is None:
        raise ValueError("Provide 'data' (features x samples matrix)")
    return pd.DataFrame(m, dtype=float)


def tics_normalize(data=None, output_path=None, **kwargs: Any):
    kw = unwrap(kwargs)
    df = _matrix(data, kwargs)
    totals = df.sum(axis=0)
    target = float(totals[totals > 0].median()) if (totals > 0).any() else 1.0
    factors = target / totals.replace(0, np.nan)
    factors = factors.fillna(1.0)
    normed = df * factors
    out = output_path or kw.get("output_path")
    if out:
        normed.to_csv(out)
    return {
        "method": "TIC (total ion current) normalization",
        "n_features": int(df.shape[0]),
        "n_samples": int(df.shape[1]),
        "target_tic": target,
        "scaling_factors": {str(k): float(v) for k, v in factors.items()},
        "normalized": normed.round(6).to_dict() if kw.get("return_matrix") else None,
        "output_path": out,
    }


def pca_scores(data=None, n_components: int = 2, **kwargs: Any):
    kw = unwrap(kwargs)
    df = _matrix(data, kwargs)
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    n_components = int(kw.get("n_components", n_components))
    log = np.log2(df.replace(0, np.nan).fillna(_EPS) + _EPS)
    x = log.T.to_numpy(dtype=float)
    x = StandardScaler().fit_transform(x)
    n_comp = min(n_components, *x.shape)
    pca = PCA(n_components=n_comp, random_state=0)
    scores = pca.fit_transform(x)
    return {
        "n_samples": int(df.shape[1]),
        "n_components": int(n_comp),
        "explained_variance_ratio": [float(v) for v in pca.explained_variance_ratio_],
        "scores": [
            {"sample": str(s), **{f"PC{i + 1}": float(row[i]) for i in range(n_comp)}}
            for s, row in zip(df.columns, scores)
        ],
    }


def plsda_scores(data=None, labels=None, n_components: int = 2, **kwargs: Any):
    kw = unwrap(kwargs)
    df = _matrix(data, kwargs)
    labels = labels if labels is not None else kw.get("labels")
    if labels is None:
        raise ValueError("plsda_scores requires 'labels' (list or {sample: label})")
    if isinstance(labels, dict):
        y = np.array([labels[c] for c in df.columns])
    else:
        y = np.asarray(list(labels))
        if y.shape[0] != df.shape[1]:
            raise ValueError("labels length must equal number of samples")
    classes = np.unique(y)
    if classes.shape[0] != 2:
        raise ValueError(f"PLS-DA supports two classes, got {classes.tolist()}")
    y01 = (y == classes[1]).astype(float)

    from sklearn.cross_decomposition import PLSRegression
    from sklearn.preprocessing import StandardScaler

    n_components = int(kw.get("n_components", n_components))
    log = np.log2(df.replace(0, np.nan).fillna(_EPS) + _EPS)
    x = StandardScaler().fit_transform(log.T.to_numpy(dtype=float))
    n_comp = min(n_components, x.shape[1])
    pls = PLSRegression(n_components=n_comp)
    pls.fit(x, y01)
    scores = pls.x_scores_
    pred = pls.predict(x).ravel()
    accuracy = float(((pred > 0.5) == (y01 > 0.5)).mean())
    return {
        "n_samples": int(df.shape[1]),
        "n_components": int(n_comp),
        "classes": [str(c) for c in classes],
        "training_accuracy": accuracy,
        "scores": [
            {"sample": str(s), "class": str(lbl), **{f"LV{i + 1}": float(row[i]) for i in range(n_comp)}}
            for s, lbl, row in zip(df.columns, y, scores)
        ],
    }


def run(operation: str, **kwargs: Any):
    ops = {"tics_normalize": tics_normalize, "pca_scores": pca_scores, "plsda_scores": plsda_scores}
    fn = ops.get(operation)
    if fn is None:
        raise ValueError(f"metabolomics_tools: unknown operation {operation!r}. Available: {sorted(ops)}")
    return fn(**kwargs)


register_skill("metabolomics_tools", run)
