"""Cross-validation skill: fold index generation, repeated scoring, and
holdout splits.

Operations
----------
- ``kfold_indices``             — K-fold train/test index pairs
- ``stratified_kfold_indices``  — stratified K-fold train/test index pairs
- ``repeated_scores``           — evaluate a sklearn estimator per fold with
  a named metric, returning a per-fold dict
- ``holdout_split``             — single train/test split
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import optional_import, skill_run, unwrap


def _get_xy(kw: dict[str, Any]):
    if "X" in kw and "y" in kw:
        X = np.asarray(kw["X"], dtype=float)
        y = np.asarray(kw["y"])
        return X, y
    if "dataframe" in kw:
        df = pd.DataFrame(kw["dataframe"])
    elif "records" in kw:
        df = pd.DataFrame(kw["records"])
    else:
        raise ValueError("Provide 'X'/'y' arrays or 'dataframe'/'records' with 'target_col'")
    target_col = kw.get("target_col")
    if target_col is None or target_col not in df.columns:
        raise ValueError("Provide a valid 'target_col'")
    y = df[target_col].to_numpy()
    X = df.drop(columns=[target_col]).select_dtypes(include=[np.number]).to_numpy(dtype=float)
    return X, y


def kfold_indices(**kwargs: Any) -> dict[str, Any]:
    """Plain K-fold train/test index pairs.

    Parameters: ``n_samples`` (or ``X``/``dataframe``), ``n_splits`` (default
    5), ``shuffle`` (default True), ``random_state``.
    """
    model_selection = optional_import("sklearn.model_selection", package="scikit-learn")

    kw = unwrap(kwargs)
    n_samples = kw.get("n_samples")
    if n_samples is None:
        X, _y = _get_xy(kw)
        n_samples = int(X.shape[0])
    n_samples = int(n_samples)

    n_splits = int(kw.get("n_splits", 5))
    n_splits = max(2, min(n_splits, n_samples))
    shuffle = bool(kw.get("shuffle", True))
    random_state = kw.get("random_state", 0)

    kf = model_selection.KFold(n_splits=n_splits, shuffle=shuffle, random_state=random_state)
    folds = [
        {"train": tr.tolist(), "test": te.tolist()}
        for tr, te in kf.split(np.arange(n_samples))
    ]
    return {"n_samples": n_samples, "n_splits": n_splits, "folds": folds}


def stratified_kfold_indices(**kwargs: Any) -> dict[str, Any]:
    """Stratified K-fold train/test index pairs.

    Parameters: ``y`` (labels) or ``dataframe`` + ``target_col``,
    ``n_splits`` (default 5), ``shuffle`` (default True), ``random_state``.
    """
    model_selection = optional_import("sklearn.model_selection", package="scikit-learn")

    kw = unwrap(kwargs)
    if "y" in kw:
        y = np.asarray(kw["y"])
    else:
        _X, y = _get_xy(kw)
    y = np.asarray(y)

    n_samples = int(y.shape[0])
    n_splits = int(kw.get("n_splits", 5))
    shuffle = bool(kw.get("shuffle", True))
    random_state = kw.get("random_state", 0)

    _, counts = np.unique(y, return_counts=True)
    min_class = int(counts.min()) if counts.size else n_samples
    n_splits = max(2, min(n_splits, min_class))

    skf = model_selection.StratifiedKFold(
        n_splits=n_splits, shuffle=shuffle, random_state=random_state
    )
    folds = [
        {"train": tr.tolist(), "test": te.tolist()}
        for tr, te in skf.split(np.zeros(n_samples), y)
    ]
    return {"n_samples": n_samples, "n_splits": n_splits, "folds": folds}


_METRICS = ("accuracy", "roc_auc", "f1", "precision", "recall", "r2", "neg_mean_squared_error")


def repeated_scores(**kwargs: Any) -> dict[str, Any]:
    """Evaluate a sklearn estimator with ``cross_val_score`` per fold.

    Parameters: ``X``/``y`` or ``dataframe`` + ``target_col``, ``model``
    (``"logistic_regression"`` (default) or ``"random_forest"``),
    ``metric`` (default ``"accuracy"``), ``n_splits`` (default 5),
    ``random_state``.
    """
    model_selection = optional_import("sklearn.model_selection", package="scikit-learn")

    kw = unwrap(kwargs)
    X, y = _get_xy(kw)

    metric = str(kw.get("metric", "accuracy"))
    if metric not in _METRICS:
        raise ValueError(f"metric must be one of {_METRICS}")
    n_splits = int(kw.get("n_splits", 5))
    n_splits = max(2, min(n_splits, X.shape[0]))
    random_state = kw.get("random_state", 0)

    model_name = kw.get("model", "logistic_regression")
    if model_name == "logistic_regression":
        linear_model = optional_import("sklearn.linear_model", package="scikit-learn")
        estimator = linear_model.LogisticRegression(max_iter=1000)
    elif model_name in ("random_forest", "random_forest_classifier"):
        ensemble = optional_import("sklearn.ensemble", package="scikit-learn")
        estimator = ensemble.RandomForestClassifier(n_estimators=50, random_state=random_state)
    elif model_name in ("random_forest_regressor",):
        ensemble = optional_import("sklearn.ensemble", package="scikit-learn")
        estimator = ensemble.RandomForestRegressor(n_estimators=50, random_state=random_state)
    elif model_name in ("linear_regression",):
        linear_model = optional_import("sklearn.linear_model", package="scikit-learn")
        estimator = linear_model.LinearRegression()
    else:
        raise ValueError(
            "model must be 'logistic_regression', 'random_forest', "
            "'random_forest_regressor', or 'linear_regression'"
        )

    cv = model_selection.KFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    scores = model_selection.cross_val_score(estimator, X, y, cv=cv, scoring=metric)
    arr = np.asarray(scores, dtype=float)
    return {
        "metric": metric,
        "model": model_name,
        "n_splits": n_splits,
        "fold_scores": [float(s) for s in arr],
        "mean_score": float(arr.mean()),
        "std_score": float(arr.std()),
    }


def holdout_split(**kwargs: Any) -> dict[str, Any]:
    """Single train/test split returning index arrays.

    Parameters: ``n_samples`` (or ``X``/``dataframe`` + ``target_col``),
    ``test_size`` (default 0.25), ``random_state``, ``stratify`` (bool).
    """
    model_selection = optional_import("sklearn.model_selection", package="scikit-learn")

    kw = unwrap(kwargs)
    y = None
    if kw.get("n_samples") is not None:
        n_samples = int(kw["n_samples"])
        if kw.get("stratify") and "y" in kw:
            y = np.asarray(kw["y"])
    else:
        X, y = _get_xy(kw)
        n_samples = int(X.shape[0])

    test_size = float(kw.get("test_size", 0.25))
    random_state = kw.get("random_state", 0)
    stratify = y if (kw.get("stratify") and y is not None) else None

    train_idx, test_idx = model_selection.train_test_split(
        np.arange(n_samples), test_size=test_size, random_state=random_state, stratify=stratify
    )
    return {
        "n_samples": int(n_samples),
        "test_size": test_size,
        "n_train": int(len(train_idx)),
        "n_test": int(len(test_idx)),
        "train": train_idx.tolist(),
        "test": test_idx.tolist(),
    }


run = skill_run(
    {
        "kfold_indices": kfold_indices,
        "stratified_kfold_indices": stratified_kfold_indices,
        "repeated_scores": repeated_scores,
        "holdout_split": holdout_split,
    }
)

register_skill("cross_validation", run)
