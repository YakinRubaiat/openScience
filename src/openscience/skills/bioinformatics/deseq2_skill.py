"""DESeq2-style differential expression skill (pure-python NB-lite fallback).

DESeq2 itself is an R package and is not available here, so this skill
implements the core of its workflow in scipy/numpy:

- ``size_factors``           — median-of-ratios normalisation factors
- ``normalize_counts``       — counts divided by size factors
- ``differential_expression``— log2 fold-change on normalised counts,
  Welch's t-test p-values on log2(normalised + 1), Benjamini-Hochberg FDR.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from openscience.skills import register_skill
from openscience.skills._common import unwrap


def _counts_frame(counts=None, **kw) -> pd.DataFrame:
    counts = counts if counts is not None else kw.get("counts")
    if counts is None:
        raise ValueError("Provide a count matrix via 'counts' (genes x samples DataFrame)")
    df = pd.DataFrame(counts)
    if not np.issubdtype(df.values.dtype, np.number):
        df = df.apply(pd.to_numeric, errors="raise")
    return df


def compute_size_factors(df: pd.DataFrame) -> pd.Series:
    """DESeq median-of-ratios size factors."""
    mat = df.to_numpy(dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        log_geo = np.where((mat > 0).all(axis=1), np.log(np.where(mat > 0, mat, 1)).mean(axis=1), np.nan)
    ratios = np.log(np.where(mat > 0, mat, np.nan)) - log_geo[:, None]
    sf = np.exp(np.nanmedian(ratios, axis=0))
    # fall back to library-size scaling when no gene is present in all samples
    if np.any(~np.isfinite(sf)) or np.any(sf <= 0):
        libsize = mat.sum(axis=0)
        sf = libsize / np.exp(np.log(libsize[libsize > 0]).mean())
    sf = np.where(np.isfinite(sf) & (sf > 0), sf, 1.0)
    return pd.Series(sf, index=df.columns, name="size_factor")


def size_factors(counts=None, **kwargs: Any):
    kw = unwrap(kwargs)
    df = _counts_frame(counts, **kw)
    sf = compute_size_factors(df)
    return {
        "size_factors": {str(k): float(v) for k, v in sf.items()},
        "n_genes": int(df.shape[0]),
        "n_samples": int(df.shape[1]),
    }


def normalize_counts(counts=None, **kwargs: Any):
    kw = unwrap(kwargs)
    df = _counts_frame(counts, **kw)
    sf = compute_size_factors(df)
    norm = df.div(sf, axis=1)
    out_path = kw.get("output_path")
    if out_path:
        norm.to_csv(out_path)
    return {
        "n_genes": int(norm.shape[0]),
        "n_samples": int(norm.shape[1]),
        "size_factors": {str(k): float(v) for k, v in sf.items()},
        "total_counts_after": {str(k): float(v) for k, v in norm.sum(axis=0).items()},
        "normalized_counts": norm.round(6).to_dict() if kw.get("return_matrix") else None,
        "output_path": out_path,
    }


def _bh_adjust(pvals: np.ndarray) -> np.ndarray:
    p = np.asarray(pvals, dtype=float)
    n = p.size
    order = np.argsort(p)
    ranked = p[order]
    q = ranked * n / (np.arange(n) + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    out = np.empty_like(q)
    out[order] = np.clip(q, 0, 1)
    return out


def differential_expression(counts=None, group_a=None, group_b=None, **kwargs: Any):
    kw = unwrap(kwargs)
    df = _counts_frame(counts, **kw)
    group_a = group_a or kw.get("group_a")
    group_b = group_b or kw.get("group_b")
    if group_a is None or group_b is None:
        # groups may come as {sample: label}
        groups = kw.get("groups")
        if groups:
            labels = pd.Series(groups)
            uniq = list(dict.fromkeys(labels))
            if len(uniq) != 2:
                raise ValueError("Exactly two groups are required")
            group_a = labels[labels == uniq[0]].index.tolist()
            group_b = labels[labels == uniq[1]].index.tolist()
        else:
            raise ValueError("Provide 'group_a' and 'group_b' sample names (or 'groups' mapping)")

    missing = [s for s in list(group_a) + list(group_b) if s not in df.columns]
    if missing:
        raise ValueError(f"Samples not found in count matrix: {missing}")

    sf = compute_size_factors(df)
    norm = df.div(sf, axis=1)
    log = np.log2(norm + 1.0)

    a = log[list(group_a)].to_numpy(dtype=float)
    b = log[list(group_b)].to_numpy(dtype=float)
    mean_a = a.mean(axis=1)
    mean_b = b.mean(axis=1)
    log2fc = mean_b - mean_a

    with np.errstate(invalid="ignore"):
        tstat, pvals = stats.ttest_ind(b, a, axis=1, equal_var=False)
    pvals = np.where(np.isfinite(pvals), pvals, 1.0)
    padj = _bh_adjust(pvals)

    base_mean = norm.mean(axis=1).to_numpy(dtype=float)
    res = pd.DataFrame(
        {
            "gene": [str(g) for g in df.index],
            "baseMean": base_mean,
            "log2FoldChange": log2fc,
            "pvalue": pvals,
            "padj": padj,
        }
    ).set_index("gene")
    res = res.sort_values("padj")

    alpha = float(kw.get("alpha", 0.05))
    lfc_thresh = float(kw.get("lfc_threshold", 1.0))
    sig = res[(res["padj"] < alpha) & (res["log2FoldChange"].abs() >= lfc_thresh)]
    top_n = int(kw.get("top", 25))
    out_path = kw.get("output_path")
    if out_path:
        res.reset_index().to_csv(out_path, index=False)

    return {
        "method": "NB-lite: median-ratio size factors + Welch t-test on log2 counts, BH FDR",
        "n_genes_tested": int(res.shape[0]),
        "n_significant": int(sig.shape[0]),
        "alpha": alpha,
        "lfc_threshold": lfc_thresh,
        "size_factors": {str(k): float(v) for k, v in sf.items()},
        "top_genes": [
            {
                "gene": str(idx),
                "log2FoldChange": float(r["log2FoldChange"]),
                "pvalue": float(r["pvalue"]),
                "padj": float(r["padj"]),
                "baseMean": float(r["baseMean"]),
            }
            for idx, r in res.head(top_n).iterrows()
        ],
        "output_path": out_path,
    }


def run(operation: str, **kwargs: Any):
    ops = {
        "differential_expression": differential_expression,
        "size_factors": size_factors,
        "normalize_counts": normalize_counts,
    }
    fn = ops.get(operation)
    if fn is None:
        raise ValueError(f"DESeq2: unknown operation {operation!r}. Available: {sorted(ops)}")
    return fn(**kwargs)


register_skill("DESeq2", run)
