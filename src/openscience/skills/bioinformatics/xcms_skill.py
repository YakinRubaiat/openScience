"""XCMS-style LC-MS feature table skill (pure python).

- ``read_features`` — load a feature CSV (features x samples intensities)
- ``rsd_filter``    — relative-standard-deviation filter per feature
  (optionally on QC samples only)
- ``ttest_features``— per-feature Welch t-test between groups, BH FDR
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from openscience.skills import register_skill
from openscience.skills._common import unwrap

_EPS = 1e-10


def _features(features=None, features_path=None, kw=None) -> pd.DataFrame:
    kw = kw or {}
    if features is not None:
        return pd.DataFrame(features, dtype=float)
    if kw.get("features") is not None:
        return pd.DataFrame(kw["features"], dtype=float)
    p = features_path or kw.get("features_path") or kw.get("path")
    if p is None:
        raise ValueError("Provide 'features' (matrix) or 'features_path' (CSV)")
    p = Path(p)
    if not p.exists():
        raise FileNotFoundError(f"Feature CSV not found: {p}")
    df = pd.read_csv(p, index_col=0)
    return df.apply(pd.to_numeric, errors="coerce").dropna(axis=1, how="all")


def read_features(features_path=None, **kwargs: Any):
    kw = unwrap(kwargs)
    df = _features(kw=kw, **{"features_path": features_path} if features_path else {})
    values = df.to_numpy(dtype=float)
    return {
        "n_features": int(df.shape[0]),
        "n_samples": int(df.shape[1]),
        "samples": [str(c) for c in df.columns][:100],
        "feature_names": [str(i) for i in df.index][:100],
        "median_intensity": float(np.nanmedian(values)),
    }


def rsd_filter(features=None, max_rsd: float | None = None, qc_samples=None, **kwargs: Any):
    kw = unwrap(kwargs)
    df = _features(features, kw=kw)
    qc = qc_samples or kw.get("qc_samples")
    sub = df[list(qc)] if qc else df
    x = sub.to_numpy(dtype=float)
    mean = x.mean(axis=1)
    sd = x.std(axis=1, ddof=1) if x.shape[1] > 1 else np.zeros(x.shape[0])
    rsd = np.where(mean != 0, sd / np.abs(mean) * 100.0, np.inf)
    max_rsd = float(kw.get("max_rsd", max_rsd if max_rsd is not None else 30.0))
    keep = rsd <= max_rsd
    kept_names = np.asarray(df.index.astype(str))[keep]
    return {
        "max_rsd_percent": max_rsd,
        "on_qc_samples": bool(qc),
        "n_features_in": int(df.shape[0]),
        "n_features_kept": int(keep.sum()),
        "kept_features": kept_names[:200].tolist(),
        "median_rsd_percent": float(np.median(rsd[np.isfinite(rsd)])) if np.isfinite(rsd).any() else None,
        "filtered_matrix": pd.DataFrame(df.to_numpy()[keep], index=df.index[keep], columns=df.columns).to_dict() if kw.get("return_matrix") else None,
    }


def ttest_features(features=None, group_a=None, group_b=None, **kwargs: Any):
    kw = unwrap(kwargs)
    df = _features(features, kw=kw)
    group_a = group_a or kw.get("group_a")
    group_b = group_b or kw.get("group_b")
    if not (group_a and group_b):
        raise ValueError("Provide 'group_a' and 'group_b' sample names")
    missing = [s for s in list(group_a) + list(group_b) if s not in df.columns]
    if missing:
        raise ValueError(f"Samples not found: {missing}")
    log = np.log2(df.replace(0, np.nan) + _EPS)
    a = log[list(group_a)].to_numpy(dtype=float)
    b = log[list(group_b)].to_numpy(dtype=float)
    log2fc = np.nanmean(b, axis=1) - np.nanmean(a, axis=1)
    with np.errstate(invalid="ignore"):
        _t, p = stats.ttest_ind(b, a, axis=1, equal_var=False, nan_policy="omit")
    p = np.where(np.isfinite(p), p, 1.0)
    order = np.argsort(p)
    q = p[order] * p.size / (np.arange(p.size) + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    padj = np.empty_like(q)
    padj[order] = np.clip(q, 0, 1)
    res = pd.DataFrame(
        {"feature": [str(i) for i in df.index], "log2fc": log2fc, "p_value": p, "padj": padj}
    ).sort_values("padj")
    alpha = float(kw.get("alpha", 0.05))
    return {
        "n_features_tested": int(res.shape[0]),
        "n_significant": int((res["padj"] < alpha).sum()),
        "top_features": res.head(int(kw.get("top", 25))).to_dict(orient="records"),
    }


def run(operation: str, **kwargs: Any):
    ops = {"read_features": read_features, "rsd_filter": rsd_filter, "ttest_features": ttest_features}
    fn = ops.get(operation)
    if fn is None:
        raise ValueError(f"xcms: unknown operation {operation!r}. Available: {sorted(ops)}")
    return fn(**kwargs)


register_skill("xcms", run)
