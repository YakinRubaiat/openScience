"""DADA2-style amplicon processing skill (pure python).

- ``remove_chimeras`` — frequency-based chimera removal: drop ASVs whose
  total abundance is <= 2 (singletons/doubletons) or below a fold threshold
  of the most abundant ASV
- ``diversity``       — Shannon / Simpson alpha diversity per sample
- ``rarefy``          — rarefaction (subsampling without replacement) of a
  feature table to even depth
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import unwrap


def _table(table=None, kw=None) -> pd.DataFrame:
    kw = kw or {}
    t = table if table is not None else kw.get("table") or kw.get("counts")
    if t is None:
        raise ValueError("Provide 'table' (features x samples count matrix)")
    return pd.DataFrame(t, dtype=float)


def remove_chimeras(table=None, max_abundance=None, min_fold_parent=None, **kwargs: Any):
    kw = unwrap(kwargs)
    df = _table(table, kwargs)
    max_abundance = kw.get("max_abundance", max_abundance)
    min_fold_parent = kw.get("min_fold_parent", min_fold_parent)
    totals = df.sum(axis=1)
    keep = np.ones(df.shape[0], dtype=bool)
    if max_abundance is not None:
        keep &= totals > float(max_abundance)
    else:
        keep &= totals > 2.0  # default: drop singletons/doubletons
    if min_fold_parent is not None:
        keep &= totals >= float(totals.max()) * float(min_fold_parent)
    dropped = df.index[~keep]
    cleaned = df.loc[keep]
    return {
        "n_features_in": int(df.shape[0]),
        "n_features_out": int(cleaned.shape[0]),
        "n_chimeras_removed": int((~keep).sum()),
        "removed_features": [str(x) for x in dropped[:100]],
        "counts_retained_fraction": float(cleaned.to_numpy().sum() / max(df.to_numpy().sum(), 1.0)),
        "table": cleaned.to_dict() if kw.get("return_table") else None,
    }


def diversity(table=None, metrics=None, **kwargs: Any):
    kw = unwrap(kwargs)
    df = _table(table, kwargs)
    metrics = metrics or kw.get("metrics") or ["shannon", "simpson", "observed"]
    x = df.to_numpy(dtype=float)
    totals = x.sum(axis=0)
    totals_safe = np.where(totals > 0, totals, 1.0)
    props = x / totals_safe
    with np.errstate(divide="ignore", invalid="ignore"):
        logp = np.where(props > 0, np.log(props), 0.0)
    shannon = -(props * logp).sum(axis=0)
    simpson = 1.0 - (props ** 2).sum(axis=0)
    observed = (x > 0).sum(axis=0)
    out = {}
    for j, sample in enumerate(df.columns):
        entry = {}
        if "shannon" in metrics:
            entry["shannon"] = float(shannon[j])
        if "simpson" in metrics:
            entry["simpson"] = float(simpson[j])
        if "observed" in metrics:
            entry["observed_features"] = int(observed[j])
        out[str(sample)] = entry
    return {
        "n_samples": int(df.shape[1]),
        "metrics": {m: {str(s): out[str(s)][m] for s in df.columns if m in out[str(s)]} for m in metrics if any(m in v for v in out.values())},
        "per_sample": out,
    }


def rarefy(table=None, depth=None, seed: int = 0, **kwargs: Any):
    kw = unwrap(kwargs)
    df = _table(table, kwargs)
    depth = int(kw.get("depth", depth) or 0)
    if depth <= 0:
        depth = int(df.sum(axis=0).min())
    rng = np.random.default_rng(int(kw.get("seed", seed)))
    x = df.to_numpy(dtype=float)
    out = np.zeros_like(x)
    dropped = []
    for j in range(x.shape[1]):
        col = x[:, j]
        total = int(col.sum())
        if total < depth:
            dropped.append(str(df.columns[j]))
            continue
        # expanded pool subsample without replacement
        pool = np.repeat(np.arange(x.shape[0]), col.astype(int))
        chosen = rng.choice(pool, size=depth, replace=False)
        counts = np.bincount(chosen, minlength=x.shape[0]).astype(float)
        out[:, j] = counts
    kept_cols = [str(c) for j, c in enumerate(df.columns) if str(c) not in dropped]
    kept = out[:, [j for j in range(x.shape[1]) if str(df.columns[j]) not in dropped]]
    return {
        "depth": depth,
        "n_samples_in": int(x.shape[1]),
        "n_samples_out": int(len(kept_cols)),
        "dropped_samples": dropped,
        "kept_samples": kept_cols,
        "seed": int(kw.get("seed", seed)),
        "table": pd.DataFrame(kept, index=df.index, columns=kept_cols).to_dict() if kw.get("return_table") else None,
    }


def run(operation: str, **kwargs: Any):
    ops = {"remove_chimeras": remove_chimeras, "diversity": diversity, "rarefy": rarefy}
    fn = ops.get(operation)
    if fn is None:
        raise ValueError(f"dada2: unknown operation {operation!r}. Available: {sorted(ops)}")
    return fn(**kwargs)


register_skill("dada2", run)
