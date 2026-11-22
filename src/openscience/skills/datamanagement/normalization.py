"""normalization_methods skill: column-wise and sample-wise normalisation.

Data is records (list-of-dicts) or a column dict; numeric columns are
normalised column-wise unless noted (log_cpm/clr are row-wise, genomics-style).
"""

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


def _numeric_cols(df: pd.DataFrame, columns: list[str] | None) -> list[str]:
    num = [str(c) for c in df.select_dtypes(include="number").columns]
    if columns is None:
        if not num:
            raise ValueError("No numeric columns to normalize")
        return num
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"Unknown columns: {missing}")
    return [str(c) for c in columns]


def _finish(df: pd.DataFrame, method: str, cols: list[str]) -> dict[str, Any]:
    return result(method=method, columns=cols, data=df.to_dict("records"))


def minmax(data: Any, columns: list[str] | None = None,
           feature_range: tuple[float, float] = (0.0, 1.0)) -> dict[str, Any]:
    """Min-max scale numeric columns into ``feature_range``."""
    lo, hi = feature_range
    df = _frame(data)
    cols = _numeric_cols(df, columns)
    for c in cols:
        col = df[c].astype(float)
        cmin, cmax = col.min(), col.max()
        span = cmax - cmin
        df[c] = (col - cmin) / span * (hi - lo) + lo if span else float(lo)
    return _finish(df, "minmax", cols)


def zscore(data: Any, columns: list[str] | None = None) -> dict[str, Any]:
    """Standardise numeric columns to zero mean / unit variance (population std)."""
    df = _frame(data)
    cols = _numeric_cols(df, columns)
    for c in cols:
        col = df[c].astype(float)
        mu, sigma = col.mean(), col.std(ddof=0)
        df[c] = (col - mu) / sigma if sigma else 0.0
    return _finish(df, "zscore", cols)


def log1p(data: Any, columns: list[str] | None = None) -> dict[str, Any]:
    """Apply log(1+x) to numeric columns."""
    df = _frame(data)
    cols = _numeric_cols(df, columns)
    for c in cols:
        if (df[c] < 0).any():
            raise ValueError(f"log1p requires non-negative values (column {c!r})")
        df[c] = np.log1p(df[c].astype(float))
    return _finish(df, "log1p", cols)


def log_cpm(data: Any, columns: list[str] | None = None,
            prior_count: float = 1.0) -> dict[str, Any]:
    """Row-wise counts-per-million + log transform (RNA-seq style).

    Each row is a sample; values are normalised by the row total.
    """
    df = _frame(data)
    cols = _numeric_cols(df, columns)
    mat = df[cols].astype(float)
    if (mat < 0).any().any():
        raise ValueError("log_cpm requires non-negative counts")
    row_sums = mat.sum(axis=1).replace(0, np.nan)
    cpm = mat.div(row_sums, axis=0) * 1e6
    df[cols] = np.log(cpm + prior_count)
    return _finish(df, "log_cpm", cols)


def quantile(data: Any, columns: list[str] | None = None) -> dict[str, Any]:
    """Quantile-normalise columns to an identical distribution (numpy).

    Ranks of each column are mapped onto the column-wise sorted means.
    """
    df = _frame(data)
    cols = _numeric_cols(df, columns)
    mat = df[cols].astype(float).to_numpy()
    order = np.argsort(mat, axis=0)
    ranks = np.empty_like(order)
    rows = np.arange(mat.shape[0])[:, None]
    ranks[order, np.arange(mat.shape[1])] = rows
    sorted_vals = np.sort(mat, axis=0)
    mean_profile = np.nanmean(sorted_vals, axis=1)
    out = mean_profile[ranks]
    nan_rows = np.isnan(mat)
    out[nan_rows] = np.nan
    df[cols] = out
    return _finish(df, "quantile", cols)


def clr(data: Any, columns: list[str] | None = None,
        pseudocount: float = 1.0) -> dict[str, Any]:
    """Row-wise centred log-ratio transform (compositional data)."""
    df = _frame(data)
    cols = _numeric_cols(df, columns)
    mat = df[cols].astype(float)
    if (mat < 0).any().any():
        raise ValueError("clr requires non-negative values")
    log_mat = np.log(mat + pseudocount)
    row_means = log_mat.mean(axis=1)
    df[cols] = log_mat.sub(row_means, axis=0)
    return _finish(df, "clr", cols)


_OPS = {
    "minmax": minmax,
    "zscore": zscore,
    "log1p": log1p,
    "log_cpm": log_cpm,
    "quantile": quantile,
    "clr": clr,
}

run = skill_run(_OPS)
register_skill("normalization_methods", run)
