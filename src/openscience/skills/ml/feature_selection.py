"""Feature selection skill: variance filtering, univariate ANOVA,
recursive feature elimination, and target-correlation reporting.

Operations
----------
- ``variance_filter``        — drop features with variance below a threshold
- ``univariate_anova``       — sklearn ``f_classif`` top-k against a target
- ``rfe``                    — RFECV with logistic regression
- ``correlate_with_target``  — per-feature correlation with a numeric target
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import skill_run, unwrap


def _get_xy(kw: dict[str, Any]):
    """Return (DataFrame X, Series y or None, feature names)."""
    if "dataframe" in kw:
        df = pd.DataFrame(kw["dataframe"])
    elif "records" in kw:
        df = pd.DataFrame(kw["records"])
    else:
        raise ValueError("Provide 'dataframe' or 'records'")

    target_col = kw.get("target_col")
    y = None
    X = df
    if target_col is not None:
        if target_col not in df.columns:
            raise ValueError(f"target_col {target_col!r} not in dataframe")
        y = df[target_col]
        X = df.drop(columns=[target_col])

    features = kw.get("features")
    if features is not None:
        X = X[[str(f) for f in features]]

    X = X.select_dtypes(include=[np.number])
    return X, y, [str(c) for c in X.columns]


def variance_filter(**kwargs: Any) -> dict[str, Any]:
    """Keep features with variance >= ``threshold`` (default 0.0)."""
    kw = unwrap(kwargs)
    X, _y, features = _get_xy(kw)
    threshold = float(kw.get("threshold", 0.0))

    variances = X.var(axis=0).to_numpy(dtype=float)
    keep = variances >= threshold
    kept_features = [f for f, k in zip(features, keep) if k]
    dropped = [f for f, k in zip(features, keep) if not k]

    return {
        "threshold": threshold,
        "n_input": len(features),
        "n_kept": int(len(kept_features)),
        "kept_features": kept_features,
        "dropped_features": dropped,
        "variances": {f: float(v) for f, v in zip(features, variances)},
        "records": X.loc[:, kept_features].to_dict(orient="records"),
    }


def univariate_anova(**kwargs: Any) -> dict[str, Any]:
    """Select top-k features by univariate ANOVA F-value against ``target``.

    Parameters: ``dataframe``/``records``, ``target_col``, ``k`` (default 10).
    """
    from openscience.skills._common import optional_import

    feature_selection = optional_import("sklearn.feature_selection", package="scikit-learn")

    kw = unwrap(kwargs)
    X, y, features = _get_xy(kw)
    if y is None:
        raise ValueError("Provide 'target_col' for ANOVA selection")

    k = kw.get("k")
    k = min(int(k), len(features)) if k is not None else len(features)
    k = max(1, k)

    f_stat, p_vals = feature_selection.f_classif(X.to_numpy(dtype=float), y.to_numpy())
    f_stat = np.asarray(f_stat, dtype=float)
    p_vals = np.asarray(p_vals, dtype=float)
    f_stat = np.nan_to_num(f_stat, nan=0.0)
    p_vals = np.nan_to_num(p_vals, nan=1.0)

    order = np.argsort(-f_stat)[:k]
    order = order[np.argsort(order)]
    kept = [features[i] for i in order]

    return {
        "k": int(k),
        "n_input": len(features),
        "kept_features": kept,
        "scores": {
            features[i]: {"f_statistic": float(f_stat[i]), "p_value": float(p_vals[i])}
            for i in range(len(features))
        },
    }


def rfe(**kwargs: Any) -> dict[str, Any]:
    """RFECV with logistic regression.

    Parameters: ``dataframe``/``records``, ``target_col``, ``min_features``
    (default 1), ``cv`` (default 5), ``step`` (default 1).
    """
    from openscience.skills._common import optional_import

    feature_selection = optional_import("sklearn.feature_selection", package="scikit-learn")
    linear_model = optional_import("sklearn.linear_model", package="scikit-learn")

    kw = unwrap(kwargs)
    X, y, features = _get_xy(kw)
    if y is None:
        raise ValueError("Provide 'target_col' for RFE")

    min_features = int(kw.get("min_features", 1))
    cv = int(kw.get("cv", 5))
    step = float(kw.get("step", 1))

    n_classes = y.nunique()
    if n_classes < 2:
        raise ValueError("RFE with logistic regression requires at least 2 classes")

    estimator = linear_model.LogisticRegression(max_iter=1000)
    rfecv = feature_selection.RFECV(
        estimator=estimator,
        step=step,
        cv=cv,
        min_features_to_select=min_features,
        scoring="accuracy",
    )
    Xn = X.to_numpy(dtype=float)
    yn = y.to_numpy()
    rfecv.fit(Xn, yn)

    support = np.asarray(rfecv.support_, dtype=bool)
    ranking = np.asarray(rfecv.ranking_, dtype=int)
    kept = [f for f, s in zip(features, support) if s]
    eliminated = [f for f, s in zip(features, support) if not s]

    return {
        "n_input": len(features),
        "n_selected": int(support.sum()),
        "selected_features": kept,
        "eliminated_features": eliminated,
        "optimal_n_features": int(rfecv.n_features_),
        "ranking": {f: int(r) for f, r in zip(features, ranking)},
    }


def correlate_with_target(**kwargs: Any) -> dict[str, Any]:
    """Report per-feature Pearson/Spearman correlation with a numeric target.

    Parameters: ``dataframe``/``records``, ``target_col``, ``method``
    (``"pearson"`` default or ``"spearman"``).
    """
    kw = unwrap(kwargs)
    method = kw.get("method", "pearson")
    if method not in ("pearson", "spearman"):
        raise ValueError("method must be 'pearson' or 'spearman'")

    X, y, features = _get_xy(kw)
    if y is None:
        raise ValueError("Provide 'target_col'")
    yn = y.to_numpy(dtype=float)

    report: list[dict[str, Any]] = []
    for f in features:
        xn = X[f].to_numpy(dtype=float)
        ok = np.isfinite(xn) & np.isfinite(yn)
        x, t = xn[ok], yn[ok]
        if x.size < 2 or np.std(x) == 0 or np.std(t) == 0:
            r = None
        elif method == "spearman":
            r = float(
                np.corrcoef(pd.Series(x).rank().to_numpy(), pd.Series(t).rank().to_numpy())[0, 1]
            )
        else:
            r = float(np.corrcoef(x, t)[0, 1])
        report.append({"feature": f, "r": r, "abs_r": abs(r) if r is not None else None})

    ranked = sorted(report, key=lambda d: (-1.0 if d["abs_r"] is None else d["abs_r"]), reverse=True)
    return {"n_features": len(features), "method": method, "correlations": ranked}


run = skill_run(
    {
        "variance_filter": variance_filter,
        "univariate_anova": univariate_anova,
        "rfe": rfe,
        "correlate_with_target": correlate_with_target,
    }
)

register_skill("feature_selection", run)
