"""Seurat-style single-cell preprocessing skill, implemented over AnnData.

Mirrors the canonical Seurat recipe using scanpy/numpy under the hood:

- ``normalize``           — library-size normalisation + log1p (LogNormalize)
- ``find_variable_genes`` — highly-variable genes (mean/dispersion method)
- ``scale``               — z-score scaling per gene (clipped)
- ``clusters_summary``    — per-cluster cell counts and mean marker expression
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import unwrap


def _adata(context=None, data=None, kw: dict | None = None):
    kw = kw or {}
    adata = data if data is not None else kw.get("data")
    if adata is None and isinstance(context, dict):
        adata = context.get("adata")
    if adata is None and isinstance(kw.get("context"), dict):
        adata = kw["context"].get("adata")
    if adata is None:
        raise ValueError("No AnnData object supplied — pass 'data' or context['adata']")
    return adata


def _X(adata):
    x = adata.X
    if hasattr(x, "toarray"):
        x = x.toarray()
    return np.asarray(x, dtype=float)


def _set_X(adata, mat: np.ndarray):
    adata.X = mat


def normalize(data=None, context=None, **kwargs: Any):
    kw = unwrap(kwargs)
    adata = _adata(context, data, kw)
    target_sum = float(kw.get("target_sum", 1e4))
    x = _X(adata)
    totals = x.sum(axis=1)
    totals = np.where(totals > 0, totals, 1.0)
    norm = np.log1p(x / totals[:, None] * target_sum)
    _set_X(adata, norm)
    adata.uns.setdefault("seurat", {})["normalize"] = {"target_sum": target_sum}
    return {
        "n_obs": int(adata.n_obs),
        "n_vars": int(adata.n_vars),
        "target_sum": target_sum,
        "median_total_before": float(np.median(totals)),
    }


def find_variable_genes(data=None, context=None, **kwargs: Any):
    kw = unwrap(kwargs)
    adata = _adata(context, data, kw)
    n_top = int(kw.get("n_top_genes", 2000))
    x = _X(adata)
    mean = x.mean(axis=0)
    var = x.var(axis=0, ddof=1) if adata.n_obs > 1 else np.zeros(adata.n_vars)
    dispersion = var / np.where(mean > 0, mean, np.nan)
    dispersion = np.where(np.isfinite(dispersion), dispersion, -np.inf)
    order = np.argsort(dispersion)[::-1]
    keep = np.zeros(adata.n_vars, dtype=bool)
    keep[order[: min(n_top, adata.n_vars)]] = True
    genes = np.asarray(adata.var_names.astype(str))
    adata.var["highly_variable"] = keep
    return {
        "n_variable_genes": int(keep.sum()),
        "variable_genes": genes[keep][:50].tolist(),
        "top_gene": str(genes[order[0]]) if adata.n_vars else None,
    }


def scale(data=None, context=None, **kwargs: Any):
    kw = unwrap(kwargs)
    adata = _adata(context, data, kw)
    max_value = float(kw.get("max_value", 10.0))
    x = _X(adata)
    mean = x.mean(axis=0)
    sd = x.std(axis=0, ddof=1) if adata.n_obs > 1 else np.ones(adata.n_vars)
    sd = np.where(sd > 0, sd, 1.0)
    z = np.clip((x - mean) / sd, -max_value, max_value)
    _set_X(adata, z)
    return {
        "n_obs": int(adata.n_obs),
        "n_vars": int(adata.n_vars),
        "max_value": max_value,
        "mean_abs_scaled": float(np.abs(z).mean()),
    }


def clusters_summary(data=None, context=None, cluster_key: str | None = None, **kwargs: Any):
    kw = unwrap(kwargs)
    adata = _adata(context, data, kw)
    cluster_key = cluster_key or kw.get("cluster_key")
    if cluster_key is None:
        for cand in ("leiden", "louvain", "seurat_clusters", "clusters"):
            if cand in adata.obs.columns:
                cluster_key = cand
                break
    if cluster_key is None or cluster_key not in adata.obs.columns:
        raise ValueError("No cluster column found — pass 'cluster_key' (e.g. 'leiden')")
    labels = adata.obs[cluster_key].astype(str)
    x = _X(adata)
    genes = np.asarray(adata.var_names.astype(str))
    summary = {}
    for cl in sorted(labels.unique()):
        mask = (labels == cl).to_numpy()
        sub = x[mask]
        mean_expr = sub.mean(axis=0) if mask.sum() else np.zeros(adata.n_vars)
        top = np.argsort(mean_expr)[::-1][:5]
        summary[str(cl)] = {
            "n_cells": int(mask.sum()),
            "mean_total_expression": float(sub.sum(axis=1).mean()) if mask.sum() else 0.0,
            "top_expressed_genes": [
                {"gene": str(genes[i]), "mean": float(mean_expr[i])} for i in top
            ],
        }
    return {"cluster_key": cluster_key, "n_clusters": len(summary), "clusters": summary}


def run(operation: str, **kwargs: Any):
    ops = {
        "normalize": normalize,
        "find_variable_genes": find_variable_genes,
        "scale": scale,
        "clusters_summary": clusters_summary,
    }
    fn = ops.get(operation)
    if fn is None:
        raise ValueError(f"seurat: unknown operation {operation!r}. Available: {sorted(ops)}")
    return fn(**kwargs)


register_skill("seurat", run)
