"""Generic proteomics statistics skill.

- ``normalize_protein_intensities`` — median-centre each sample
- ``ttest_proteins``                — per-protein Welch t-test, BH FDR
- ``volcano_data``                  — (log2FC, -log10(p)) volcano payload
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from openscience.skills import register_skill
from openscience.skills._common import unwrap

_EPS = 1e-10


def _matrix(intensities=None, kw=None) -> pd.DataFrame:
    kw = kw or {}
    m = intensities if intensities is not None else kw.get("intensities")
    if m is None:
        raise ValueError("Provide 'intensities' (proteins x samples matrix)")
    return pd.DataFrame(m, dtype=float)


def _normalize(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float]]:
    medians = df.replace(0, np.nan).median(axis=0)
    target = float(medians.dropna().median())
    factors = target / medians.replace(0, np.nan)
    factors = factors.fillna(1.0)
    normed = df * factors
    return normed, {str(k): float(v) for k, v in factors.items()}


def normalize_protein_intensities(intensities=None, output_path=None, **kwargs: Any):
    kw = unwrap(kwargs)
    df = _matrix(intensities, kwargs)
    normed, factors = _normalize(df)
    out = output_path or kw.get("output_path")
    if out:
        normed.to_csv(out)
    return {
        "n_proteins": int(df.shape[0]),
        "n_samples": int(df.shape[1]),
        "normalization": "median-centering",
        "scaling_factors": factors,
        "sample_medians_after": {
            str(c): float(normed[c].replace(0, np.nan).median()) for c in normed.columns
        },
        "normalized": normed.round(6).to_dict() if kw.get("return_matrix") else None,
        "output_path": out,
    }


def _bh(p: np.ndarray) -> np.ndarray:
    order = np.argsort(p)
    q = p[order] * p.size / (np.arange(p.size) + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    out = np.empty_like(q)
    out[order] = np.clip(q, 0, 1)
    return out


def ttest_proteins(intensities=None, group_a=None, group_b=None, **kwargs: Any):
    kw = unwrap(kwargs)
    df = _matrix(intensities, kwargs)
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
    padj = _bh(p)
    res = pd.DataFrame(
        {"protein": [str(i) for i in df.index], "log2fc": log2fc, "p_value": p, "padj": padj}
    ).sort_values("padj")
    alpha = float(kw.get("alpha", 0.05))
    sig = res[(res["padj"] < alpha) & (res["log2fc"].abs() >= float(kw.get("lfc_threshold", 1.0)))]
    return {
        "n_proteins_tested": int(res.shape[0]),
        "n_significant": int(sig.shape[0]),
        "alpha": alpha,
        "top_proteins": res.head(int(kw.get("top", 25))).to_dict(orient="records"),
    }


def volcano_data(intensities=None, group_a=None, group_b=None, **kwargs: Any):
    kw = unwrap(kwargs)
    stats_res = ttest_proteins(intensities, group_a, group_b, **{**kwargs, "top": 10**9})
    df = pd.DataFrame(stats_res["top_proteins"])
    if df.empty:
        return {"n_points": 0, "points": []}
    df["neg_log10_p"] = -np.log10(df["p_value"].clip(lower=_EPS))
    sig = (df["padj"] < float(kw.get("alpha", 0.05))) & (df["log2fc"].abs() >= float(kw.get("lfc_threshold", 1.0)))
    df["significant"] = sig
    points = df.to_dict(orient="records")
    return {
        "n_points": len(points),
        "n_significant": int(sig.sum()),
        "x": "log2foldchange",
        "y": "-log10(p_value)",
        "points": points,
    }


def run(operation: str, **kwargs: Any):
    ops = {
        "normalize_protein_intensities": normalize_protein_intensities,
        "ttest_proteins": ttest_proteins,
        "volcano_data": volcano_data,
    }
    fn = ops.get(operation)
    if fn is None:
        raise ValueError(f"proteomics_tools: unknown operation {operation!r}. Available: {sorted(ops)}")
    return fn(**kwargs)


register_skill("proteomics_tools", run)
