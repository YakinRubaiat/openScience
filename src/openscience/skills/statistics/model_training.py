"""model_training: sklearn classifiers/regressors with cross-validation."""

from __future__ import annotations

from typing import Any

import numpy as np

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run


def _xy(X: Any, y: Any, feature_names: Any | None) -> tuple[np.ndarray, np.ndarray, list[str]]:
    Xm = np.asarray(X, dtype=float)
    if Xm.ndim == 1:
        Xm = Xm.reshape(-1, 1)
    yv = np.asarray(y)
    names = list(feature_names) if feature_names else [f"x{i + 1}" for i in range(Xm.shape[1])]
    return Xm, yv, names


def _cv(estimator: Any, Xm: np.ndarray, yv: np.ndarray, cv: int, scoring: str) -> dict[str, Any]:
    from sklearn.model_selection import cross_val_score

    scores = cross_val_score(estimator, Xm, yv, cv=cv, scoring=scoring)
    return {
        "cv": int(cv),
        "scoring": scoring,
        "cv_scores": [float(s) for s in scores],
        "cv_mean": float(scores.mean()),
        "cv_std": float(scores.std()),
    }


def _importances(estimator: Any, Xm: np.ndarray, yv: np.ndarray, names: list[str]) -> list[dict[str, Any]] | None:
    from sklearn.inspection import permutation_importance

    estimator.fit(Xm, yv)
    if hasattr(estimator, "feature_importances_"):
        imp = estimator.feature_importances_
        method = "gini_importance"
    elif hasattr(estimator, "coef_"):
        imp = np.abs(np.asarray(estimator.coef_).ravel()[: Xm.shape[1]])
        method = "abs_coefficient"
    else:
        pi = permutation_importance(estimator, Xm, yv, n_repeats=5, random_state=0)
        imp = pi.importances_mean
        method = "permutation"
    total = float(np.sum(imp)) or 1.0
    return [
        {"feature": names[i], "importance": float(imp[i]), "importance_fraction": float(imp[i] / total)}
        for i in np.argsort(imp)[::-1]
    ] if imp.size == len(names) else None


def train_classifier(
    X: Any,
    y: Any,
    model_type: str = "logistic",
    cv: int = 5,
    feature_names: Any | None = None,
    random_state: int = 0,
    **kwargs: Any,
) -> dict[str, Any]:
    """Train a logistic-regression or random-forest classifier with cross_val_score."""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression

    Xm, yv, names = _xy(X, y, feature_names)
    cv = int(cv)
    if model_type in ("logistic", "logistic_regression", "lr"):
        estimator = LogisticRegression(max_iter=1000, random_state=random_state)
        model_label = "logistic_regression"
        scoring = "accuracy"
    elif model_type in ("rf", "random_forest"):
        estimator = RandomForestClassifier(n_estimators=100, random_state=random_state)
        model_label = "random_forest"
        scoring = "accuracy"
    else:
        raise ValueError(f"Unknown model_type {model_type!r}; use 'logistic' or 'rf'")

    scores_out = _cv(estimator, Xm, yv, cv, scoring)
    estimator.fit(Xm, yv)
    return result(
        task="classification",
        model=model_label,
        n_samples=int(Xm.shape[0]),
        n_features=int(Xm.shape[1]),
        classes=sorted({str(c) for c in np.unique(yv)}),
        train_accuracy=float(estimator.score(Xm, yv)),
        feature_importance=_importances(estimator, Xm, yv, names),
        **scores_out,
    )


def train_regressor(
    X: Any,
    y: Any,
    model_type: str = "linear",
    cv: int = 5,
    feature_names: Any | None = None,
    random_state: int = 0,
    **kwargs: Any,
) -> dict[str, Any]:
    """Train a linear or random-forest regressor with cross_val_score (R^2)."""
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import LinearRegression

    Xm, yv, names = _xy(X, y, feature_names)
    yv = yv.astype(float)
    cv = int(cv)
    if model_type in ("linear", "linear_regression", "ols", "lr"):
        estimator = LinearRegression()
        model_label = "linear_regression"
    elif model_type in ("rf", "random_forest"):
        estimator = RandomForestRegressor(n_estimators=100, random_state=random_state)
        model_label = "random_forest"
    else:
        raise ValueError(f"Unknown model_type {model_type!r}; use 'linear' or 'rf'")

    scores_out = _cv(estimator, Xm, yv, cv, "r2")
    estimator.fit(Xm, yv)
    return result(
        task="regression",
        model=model_label,
        n_samples=int(Xm.shape[0]),
        n_features=int(Xm.shape[1]),
        train_r2=float(estimator.score(Xm, yv)),
        feature_importance=_importances(estimator, Xm, yv, names),
        **scores_out,
    )


def feature_importance(
    X: Any,
    y: Any,
    model_type: str = "rf",
    task: str = "classification",
    feature_names: Any | None = None,
    random_state: int = 0,
    **kwargs: Any,
) -> dict[str, Any]:
    """Feature importances ranked descending (Gini for RF, |coef| for linear)."""
    if task == "regression":
        out = train_regressor(X, y, model_type=model_type, feature_names=feature_names,
                              random_state=random_state, **kwargs)
    else:
        out = train_classifier(X, y, model_type=model_type, feature_names=feature_names,
                               random_state=random_state, **kwargs)
    return result(
        task=out["task"],
        model=out["model"],
        feature_importance=out["feature_importance"],
    )


run = skill_run(
    {
        "train_classifier": train_classifier,
        "train_regressor": train_regressor,
        "feature_importance": feature_importance,
    }
)

register_skill("model_training", run)
