"""outlier_detection skill: z-score, IQR and IsolationForest outlier detection."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run


def _frame(data: Any) -> pd.DataFrame:
    if isinstance(data, pd.DataFrame):
        return data
    return pd.DataFrame(data)


def _numeric(df: pd.DataFrame, column: str | None) -> tuple[pd.DataFrame, list[str]]:
    num = df.select_dtypes(include="number")
    if column is not None:
        if column not in num.columns:
            raise ValueError(f"Column {column!r} is not numeric or missing")
        num = num[[column]]
    if num.empty:
        raise ValueError("No numeric columns available for outlier detection")
    return num, [str(c) for c in num.columns]


def zscore(data: Any, column: str | None = None, threshold: float = 3.0) -> dict[str, Any]:
    """Flag rows whose |z-score| exceeds ``threshold`` (scipy.stats.zscore)."""
    from scipy import stats as ss

    df = _frame(data)
    num, cols = _numeric(df, column)
    z = np.asarray(ss.zscore(num, axis=0, nan_policy="omit"))
    if z.ndim == 1:
        z = z.reshape(-1, 1)
    mask = np.nanmax(np.abs(z), axis=1) > threshold
    out_cols = [cols[i] for i in range(len(cols))]
    return result(
        method="zscore",
        threshold=threshold,
        columns=out_cols,
        z_scores={cols[i]: z[:, i].tolist() for i in range(len(cols))},
        outlier_indices=[int(i) for i in np.flatnonzero(mask)],
        n_outliers=int(mask.sum()),
    )


def iqr(data: Any, column: str | None = None, multiplier: float = 1.5) -> dict[str, Any]:
    """Flag rows outside [Q1 - k*IQR, Q3 + k*IQR] for any examined column."""
    df = _frame(data)
    num, cols = _numeric(df, column)
    mask = np.zeros(len(df), dtype=bool)
    fences: dict[str, dict[str, float]] = {}
    for c in cols:
        q1, q3 = float(num[c].quantile(0.25)), float(num[c].quantile(0.75))
        iqr_val = q3 - q1
        lo, hi = q1 - multiplier * iqr_val, q3 + multiplier * iqr_val
        fences[c] = {"q1": q1, "q3": q3, "lower": lo, "upper": hi}
        mask |= (num[c] < lo).to_numpy() | (num[c] > hi).to_numpy()
    return result(
        method="iqr",
        multiplier=multiplier,
        columns=cols,
        fences=fences,
        outlier_indices=[int(i) for i in np.flatnonzero(mask)],
        n_outliers=int(mask.sum()),
    )


def isolation_forest(data: Any, contamination: float = 0.1,
                     random_state: int = 42) -> dict[str, Any]:
    """Flag outliers with sklearn's IsolationForest over all numeric columns."""
    from sklearn.ensemble import IsolationForest

    df = _frame(data)
    num, cols = _numeric(df, None)
    x = num.fillna(num.median()).to_numpy(dtype=float, copy=True)
    model = IsolationForest(contamination=contamination, random_state=random_state)
    try:
        labels = model.fit_predict(x)
        scores = model.decision_function(x)
    except ValueError as exc:
        # numpy's _CopyMode identity breaks when numpy gets reloaded
        # (e.g. under coverage instrumentation); surface a clear error.
        if "_CopyMode" in str(exc):
            raise RuntimeError(
                "sklearn is unusable in this interpreter because numpy was "
                "reloaded (e.g. under coverage). Original error: "
                f"{exc}"
            ) from exc
        raise
    mask = labels == -1
    return result(
        method="isolation_forest",
        contamination=contamination,
        columns=cols,
        outlier_indices=[int(i) for i in np.flatnonzero(mask)],
        n_outliers=int(mask.sum()),
        anomaly_scores=[float(s) for s in scores],
    )


def remove(data: Any, method: str = "iqr", **kwargs) -> dict[str, Any]:
    """Remove outliers detected by ``method`` (zscore/iqr/isolation_forest)."""
    detectors = {"zscore": zscore, "iqr": iqr, "isolation_forest": isolation_forest}
    if method not in detectors:
        raise ValueError(f"Unknown removal method {method!r}; available: {sorted(detectors)}")
    df = _frame(data)
    flagged = detectors[method](data, **kwargs)
    drop_idx = set(flagged["outlier_indices"])
    keep = [i for i in range(len(df)) if i not in drop_idx]
    cleaned = df.iloc[keep]
    return result(
        method=method,
        n_rows_before=int(len(df)),
        n_rows_after=int(len(cleaned)),
        n_removed=int(len(df) - len(cleaned)),
        removed_indices=sorted(drop_idx),
        data=cleaned.to_dict("records"),
    )


_OPS = {"zscore": zscore, "iqr": iqr, "isolation_forest": isolation_forest, "remove": remove}

run = skill_run(_OPS)
register_skill("outlier_detection", run)
