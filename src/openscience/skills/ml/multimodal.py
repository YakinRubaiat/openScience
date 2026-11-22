"""Multimodal integration skill: fuse dataframes from different modalities.

Operations
----------
- ``late_fusion_concat``            — outer/inner concat of feature matrices
  on their index
- ``early_fusion_pca``              — concat then PCA to shared latent space
- ``correlation_between_modalities``— per-pair Pearson correlation between
  matched features of two modalities
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import skill_run, unwrap


def _get_frames(kw: dict[str, Any]) -> dict[str, pd.DataFrame]:
    """Accept ``modalities`` dict or varargs ``df_<name>`` keys."""
    if "modalities" in kw and isinstance(kw["modalities"], dict):
        return {str(k): pd.DataFrame(v) for k, v in kw["modalities"].items()}
    frames: dict[str, pd.DataFrame] = {}
    for k, v in kw.items():
        if k.startswith("df_"):
            frames[k[3:]] = pd.DataFrame(v)
    if not frames and "dataframe" in kw:
        frames["df"] = pd.DataFrame(kw["dataframe"])
    if not frames:
        raise ValueError("Provide 'modalities' (dict of name -> dataframe) or df_<name> keys")
    return frames


def late_fusion_concat(**kwargs: Any) -> dict[str, Any]:
    """Concatenate modality feature matrices along their sample index.

    Parameters: ``modalities`` (dict name -> dataframe-like), ``join``
    (``"outer"`` default or ``"inner"``), ``prefix`` (bool, default True:
    prefix columns with modality name).
    """
    kw = unwrap(kwargs)
    frames = _get_frames(kw)
    join = kw.get("join", "outer")
    if join not in ("outer", "inner"):
        raise ValueError("join must be 'outer' or 'inner'")
    prefix = bool(kw.get("prefix", True))

    renamed: list[pd.DataFrame] = []
    for name, df in frames.items():
        d = df.copy()
        if prefix:
            d.columns = [f"{name}__{c}" for c in d.columns]
        renamed.append(d)

    if join == "inner":
        fused = pd.concat(renamed, axis=1, join="inner")
    else:
        fused = pd.concat(renamed, axis=1, join="outer")

    fused = fused.sort_index()
    return {
        "n_samples": int(fused.shape[0]),
        "n_features": int(fused.shape[1]),
        "modality_features": {name: int(df.shape[1]) for name, df in frames.items()},
        "columns": [str(c) for c in fused.columns],
        "records": fused.reset_index().rename(columns={"index": "sample"}).to_dict(orient="records"),
    }


def early_fusion_pca(**kwargs: Any) -> dict[str, Any]:
    """Concat modalities (inner join), z-score, and run PCA.

    Parameters: ``modalities``, ``n_components`` (default min(5, n_features)),
    ``scale`` (default True).
    """
    from openscience.skills._common import optional_import

    decomposition = optional_import("sklearn.decomposition", package="scikit-learn")

    kw = unwrap(kwargs)
    frames = _get_frames(kw)
    n_components_kw = kw.get("n_components")
    scale = bool(kw.get("scale", True))

    renamed: list[pd.DataFrame] = []
    for name, df in frames.items():
        d = df.copy()
        d.columns = [f"{name}__{c}" for c in d.columns]
        renamed.append(d)
    fused = pd.concat(renamed, axis=1, join="inner").sort_index()
    fused = fused.dropna(axis=0, how="any")
    X = fused.to_numpy(dtype=float)

    if scale and X.shape[0] > 0:
        mean = X.mean(axis=0)
        std = X.std(axis=0)
        std[std == 0] = 1.0
        X = (X - mean) / std

    n_feat = X.shape[1]
    n_samp = X.shape[0]
    max_comp = max(1, min(n_feat, n_samp))
    n_components = int(n_components_kw) if n_components_kw is not None else min(5, max_comp)
    n_components = max(1, min(n_components, max_comp))

    pca = decomposition.PCA(n_components=n_components)
    scores = pca.fit_transform(X)

    return {
        "n_samples": int(n_samp),
        "n_features": int(n_feat),
        "n_components": int(n_components),
        "explained_variance_ratio": [float(v) for v in pca.explained_variance_ratio_],
        "cumulative_explained_variance": [
            float(v) for v in np.cumsum(pca.explained_variance_ratio_)
        ],
        "scores": scores.tolist(),
        "loadings": pca.components_.tolist(),
        "feature_names": [str(c) for c in fused.columns],
    }


def correlation_between_modalities(**kwargs: Any) -> dict[str, Any]:
    """Pearson correlation between matched features of two modalities.

    Parameters: ``df_a`` and ``df_b`` (dataframe-likes) or ``modalities``
    with exactly two entries; ``method`` (``"pearson"`` default or
    ``"spearman"``).
    """
    kw = unwrap(kwargs)
    method = kw.get("method", "pearson")
    if method not in ("pearson", "spearman"):
        raise ValueError("method must be 'pearson' or 'spearman'")

    if "df_a" in kw and "df_b" in kw:
        a = pd.DataFrame(kw["df_a"])
        b = pd.DataFrame(kw["df_b"])
        name_a, name_b = str(kw.get("name_a", "a")), str(kw.get("name_b", "b"))
    else:
        frames = _get_frames(kw)
        if len(frames) != 2:
            raise ValueError("Provide exactly two modalities, or df_a and df_b")
        (name_a, a), (name_b, b) = frames.items()

    shared = a.index.intersection(b.index)
    a = a.loc[shared]
    b = b.loc[shared]

    a_num = a.select_dtypes(include=[np.number])
    b_num = b.select_dtypes(include=[np.number])
    common_cols = [c for c in a_num.columns if c in b_num.columns]
    cols_a = list(a_num.columns) if not common_cols else common_cols
    cols_b = list(b_num.columns) if not common_cols else common_cols

    pairs: list[dict[str, Any]] = []
    for ca in cols_a:
        for cb in cols_b:
            x = a[ca].to_numpy(dtype=float)
            y = b[cb].to_numpy(dtype=float)
            ok = np.isfinite(x) & np.isfinite(y)
            x, y = x[ok], y[ok]
            if x.size < 2 or np.std(x) == 0 or np.std(y) == 0:
                r = None
            elif method == "spearman":
                r = float(
                    np.corrcoef(
                        pd.Series(x).rank().to_numpy(), pd.Series(y).rank().to_numpy()
                    )[0, 1]
                )
            else:
                r = float(np.corrcoef(x, y)[0, 1])
            pairs.append(
                {"feature_a": str(ca), "feature_b": str(cb), "n": int(x.size), "r": r}
            )
    return {
        "modality_a": name_a,
        "modality_b": name_b,
        "n_samples": int(len(shared)),
        "method": method,
        "pairs": pairs,
    }


run = skill_run(
    {
        "late_fusion_concat": late_fusion_concat,
        "early_fusion_pca": early_fusion_pca,
        "correlation_between_modalities": correlation_between_modalities,
    }
)

register_skill("multimodal_integration", run)
