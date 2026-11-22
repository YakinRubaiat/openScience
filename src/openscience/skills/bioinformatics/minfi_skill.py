"""minfi-style methylation array skill (pure python proxies).

minfi is an R/Bioconductor package for Illumina 450k/EPIC arrays. This skill
implements the equivalent core steps in numpy/pandas:

- ``read_idat_summary``   — load a CSV proxy of IDAT-extracted signal
  (columns of methylated/unmethylated intensities per probe) and compute
  beta values
- ``detection_pvalues``   — given a beta table, estimate the fraction of
  probes per sample above a detection threshold
- ``preprocess_normalize``— quantile normalisation of a beta matrix
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import unwrap


def read_idat_summary(csv_path=None, **kwargs: Any):
    kw = unwrap(kwargs)
    p = csv_path or kw.get("csv_path") or kw.get("path")
    if p is None:
        raise ValueError("read_idat_summary requires 'csv_path'")
    p = Path(p)
    if not p.exists():
        raise FileNotFoundError(f"IDAT summary CSV not found: {p}")
    df = pd.read_csv(p, index_col=0)
    lower = {c.lower(): c for c in df.columns}
    meth_col = next((lower[c] for c in lower if c.startswith("meth")), None)
    unmeth_col = next((lower[c] for c in lower if c.startswith("unmeth")), None)
    if meth_col is None or unmeth_col is None:
        raise ValueError(
            "CSV must contain methylated/unmethylated intensity columns "
            f"(found: {list(df.columns)})"
        )
    offset = float(kw.get("offset", 100.0))
    meth = df[meth_col].astype(float)
    unmeth = df[unmeth_col].astype(float)
    beta = meth / (meth + unmeth + offset)
    df["beta"] = beta
    return {
        "path": str(p),
        "n_probes": int(df.shape[0]),
        "columns": [str(c) for c in df.columns],
        "mean_beta": float(beta.mean()),
        "beta_preview": {str(k): float(v) for k, v in beta.head(20).items()},
    }


def detection_pvalues(betas=None, threshold: float | None = None, **kwargs: Any):
    """Fraction of probes above a beta threshold per sample (detection proxy)."""
    kw = unwrap(kwargs)
    betas = betas if betas is not None else kw.get("betas")
    if betas is None:
        raise ValueError("detection_pvalues requires 'betas' (probes x samples)")
    df = pd.DataFrame(betas, dtype=float)
    threshold = float(kw.get("threshold", threshold if threshold is not None else 0.5))
    frac = (df > threshold).mean(axis=0)
    return {
        "threshold": threshold,
        "n_probes": int(df.shape[0]),
        "n_samples": int(df.shape[1]),
        "fraction_above_threshold": {str(k): float(v) for k, v in frac.items()},
        "mean_fraction": float(frac.mean()),
    }


def preprocess_normalize(betas=None, output_path=None, **kwargs: Any):
    """Quantile-normalise a probes x samples beta matrix."""
    kw = unwrap(kwargs)
    betas = betas if betas is not None else kw.get("betas")
    if betas is None:
        raise ValueError("preprocess_normalize requires 'betas' (probes x samples)")
    df = pd.DataFrame(betas, dtype=float)
    x = df.to_numpy(dtype=float)
    rank_means = np.sort(x, axis=0).mean(axis=1)
    normed = np.empty_like(x)
    for j in range(x.shape[1]):
        order = np.argsort(np.argsort(x[:, j]))
        # map each value to the mean of the sorted column at its rank
        ranks = order  # rank of each element
        normed[:, j] = rank_means[ranks]
    out_df = pd.DataFrame(normed, index=df.index, columns=df.columns)
    out = output_path or kw.get("output_path")
    if out:
        out_df.to_csv(out)
    sample_means_before = x.mean(axis=0)
    sample_means_after = normed.mean(axis=0)
    return {
        "n_probes": int(df.shape[0]),
        "n_samples": int(df.shape[1]),
        "sample_means_before": {str(c): float(m) for c, m in zip(df.columns, sample_means_before)},
        "sample_means_after": {str(c): float(m) for c, m in zip(df.columns, sample_means_after)},
        "output_path": out,
        "normalized_preview": out_df.head(10).round(6).to_dict() if kw.get("return_matrix") else None,
    }


def run(operation: str, **kwargs: Any):
    ops = {
        "read_idat_summary": read_idat_summary,
        "detection_pvalues": detection_pvalues,
        "preprocess_normalize": preprocess_normalize,
    }
    fn = ops.get(operation)
    if fn is None:
        raise ValueError(f"minfi: unknown operation {operation!r}. Available: {sorted(ops)}")
    return fn(**kwargs)


register_skill("minfi", run)
