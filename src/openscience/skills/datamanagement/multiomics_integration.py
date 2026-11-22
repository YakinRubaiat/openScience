"""multiomics_integration skill: combine omics matrices and embed jointly."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run


def _frame(data: Any) -> pd.DataFrame:
    if isinstance(data, pd.DataFrame):
        return data.copy()
    return pd.DataFrame(data)


def _require_id(df: pd.DataFrame, id_column: str, name: str) -> pd.DataFrame:
    if id_column not in df.columns:
        raise ValueError(f"{name} is missing sample id column {id_column!r}")
    return df.set_index(id_column)


def concat_features(datasets: list[Any], id_column: str,
                    prefixes: list[str] | None = None) -> dict[str, Any]:
    """Horizontally concatenate omics blocks on a shared sample id.

    Duplicate feature names across blocks are disambiguated with ``prefixes``
    (defaults to block0_, block1_, ...).
    """
    if not datasets:
        raise ValueError("concat_features requires at least one dataset")
    prefixes = prefixes or [f"block{i}_" for i in range(len(datasets))]
    if len(prefixes) != len(datasets):
        raise ValueError("'prefixes' must match number of datasets")
    frames = []
    for i, ds in enumerate(datasets):
        df = _require_id(_frame(ds), id_column, f"dataset {i}")
        rename = {c: c if str(c).startswith(prefixes[i]) else f"{prefixes[i]}{c}"
                  for c in df.columns}
        frames.append(df.rename(columns={c: str(nc) for c, nc in rename.items()}))
    merged = pd.concat(frames, axis=1, join="outer")
    merged.index.name = id_column
    out = merged.reset_index()
    return result(
        n_samples=int(len(out)),
        n_features=int(out.shape[1] - 1),
        blocks=len(datasets),
        data=out.to_dict("records"),
    )


def inner_join_samples(datasets: list[Any], id_column: str) -> dict[str, Any]:
    """Keep only samples present in every omics block (inner join on id)."""
    if not datasets:
        raise ValueError("inner_join_samples requires at least one dataset")
    merged = None
    for i, ds in enumerate(datasets):
        df = _frame(ds)
        if id_column not in df.columns:
            raise ValueError(f"dataset {i} missing id column {id_column!r}")
        rename = {c: f"b{i}_{c}" for c in df.columns if c != id_column}
        df = df.rename(columns={c: str(nc) for c, nc in rename.items()})
        merged = df if merged is None else merged.merge(df, on=id_column, how="inner")
    return result(
        n_samples=int(len(merged)),
        n_features=int(merged.shape[1] - 1),
        sample_ids=[str(v) for v in merged[id_column]],
        data=merged.to_dict("records"),
    )


def pca_integrated(datasets: list[Any], id_column: str,
                   n_components: int = 2,
                   scale: bool = True) -> dict[str, Any]:
    """Inner-join omics blocks and compute a joint PCA embedding (numpy SVD).

    Each block is z-scored column-wise before concatenation so blocks with
    different scales contribute comparably.
    """
    joined = inner_join_samples(datasets, id_column)
    df = pd.DataFrame(joined["data"]).set_index(id_column)
    num = df.select_dtypes(include="number")
    if num.empty:
        raise ValueError("No numeric features to embed")
    x = num.to_numpy(dtype=float)
    if scale:
        mu, sigma = x.mean(axis=0), x.std(axis=0)
        sigma[sigma == 0] = 1.0
        x = (x - mu) / sigma
    else:
        x = x - x.mean(axis=0)
    n_components = max(1, min(n_components, x.shape[0] - 1, x.shape[1]))
    _, s, vt = np.linalg.svd(x, full_matrices=False)
    scores = x @ vt[:n_components].T
    explained = (s**2) / max(1, len(x) - 1)
    var_total = float(np.sum(np.var(x, axis=0, ddof=1)) if x.shape[0] > 1 else 1.0)
    return result(
        n_samples=int(x.shape[0]),
        n_features=int(num.shape[1]),
        n_components=int(n_components),
        sample_ids=[str(v) for v in df.index],
        embedding=scores.tolist(),
        variance_explained_ratio=[float(v / var_total) for v in explained[:n_components]],
    )


_OPS = {
    "concat_features": concat_features,
    "inner_join_samples": inner_join_samples,
    "pca_integrated": pca_integrated,
}

run = skill_run(_OPS)
register_skill("multiomics_integration", run)
