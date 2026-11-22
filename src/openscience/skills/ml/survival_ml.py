"""Survival machine-learning skill: cross-validated Cox scores, Kaplan-Meier
AUC at a time point, and simple risk grouping.

Operations
----------
- ``cox_cv_score``     — K-fold cross-validated concordance index for a Cox
  proportional-hazards model (lifelines + sklearn KFold)
- ``km_auc_at_time``   — integrated Kaplan-Meier survival up to time ``t``
  per group (area under the KM curve)
- ``risk_groups``      — median split on a risk score plus log-rank p-value
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import skill_run, unwrap


def _build_df(kw: dict[str, Any]) -> pd.DataFrame:
    df = pd.DataFrame(kw["dataframe"])
    duration_col = kw.get("duration_col", "duration")
    event_col = kw.get("event_col", "event")
    if duration_col not in df.columns or event_col not in df.columns:
        raise ValueError(f"Columns {duration_col!r}/{event_col!r} must be present")
    return df


def cox_cv_score(**kwargs: Any) -> dict[str, Any]:
    """K-fold cross-validated concordance index for a Cox PH model.

    Parameters: ``dataframe`` (dict of columns), ``duration_col``,
    ``event_col``, ``n_splits`` (default 5), ``shuffle`` (default True),
    ``random_state`` (default 0).
    """
    from openscience.skills._common import optional_import

    lifelines = optional_import("lifelines")
    model_selection = optional_import("sklearn.model_selection", package="scikit-learn")

    kw = unwrap(kwargs)
    df = _build_df(kw)
    duration_col = kw.get("duration_col", "duration")
    event_col = kw.get("event_col", "event")
    n_splits = int(kw.get("n_splits", 5))
    shuffle = bool(kw.get("shuffle", True))
    random_state = kw.get("random_state", 0)

    n_splits = max(2, min(n_splits, len(df)))
    kf = model_selection.KFold(n_splits=n_splits, shuffle=shuffle, random_state=random_state)

    cph = lifelines.CoxPHFitter()
    scores: list[float] = []
    n_samples = df.shape[0]
    for fold_idx, (train_idx, test_idx) in enumerate(kf.split(df)):
        train = df.iloc[train_idx]
        test = df.iloc[test_idx]
        try:
            cph.fit(train, duration_col=duration_col, event_col=event_col)
            c = float(cph.score(test, scoring_method="concordance_index"))
        except Exception:
            c = float("nan")
        scores.append(c)

    arr = np.asarray(scores, dtype=float)
    finite = arr[np.isfinite(arr)]
    return {
        "n_splits": n_splits,
        "n_samples": int(n_samples),
        "fold_scores": [float(s) for s in scores],
        "mean_concordance": float(np.nanmean(arr)) if finite.size else None,
        "std_concordance": float(np.nanstd(arr)) if finite.size else None,
    }


def km_auc_at_time(**kwargs: Any) -> dict[str, Any]:
    """Area under the Kaplan-Meier curve up to time ``t`` per group.

    Parameters: ``durations``, ``events``, ``groups``, ``time`` (upper
    integration limit).
    """
    from openscience.skills._common import optional_import

    lifelines = optional_import("lifelines")

    kw = unwrap(kwargs)
    durations = np.asarray(kw["durations"], dtype=float)
    events = np.asarray(kw["events"], dtype=int)
    groups = np.asarray(kw["groups"])
    t_max = float(kw["time"])

    kmf = lifelines.KaplanMeierFitter()
    out: dict[str, Any] = {"time": t_max, "groups": {}}
    for g in np.unique(groups):
        sub_d = durations[groups == g]
        sub_e = events[groups == g]
        if len(sub_d) == 0:
            continue
        kmf.fit(sub_d, sub_e, label=str(g))
        grid = np.linspace(0.0, t_max, 200)
        surv = kmf.survival_function_at_times(grid).values.astype(float)
        surv = np.nan_to_num(surv, nan=1.0)
        auc = float(np.trapezoid(surv, grid))
        out["groups"][str(g)] = {
            "n": int(len(sub_d)),
            "auc": auc,
            "mean_survival_time": auc,  # RMST up to t
        }
    return out


def risk_groups(**kwargs: Any) -> dict[str, Any]:
    """Median split on risk score + log-rank test between halves.

    Parameters: ``durations``, ``events``, ``risk_scores``.
    """
    from openscience.skills._common import optional_import

    stats = optional_import("lifelines.statistics", package="lifelines")

    kw = unwrap(kwargs)
    durations = np.asarray(kw["durations"], dtype=float)
    events = np.asarray(kw["events"], dtype=int)
    risk = np.asarray(kw["risk_scores"], dtype=float)

    median = float(np.median(risk))
    labels = np.where(risk > median, "high", "low")

    hi = labels == "high"
    lo = labels == "low"
    result: dict[str, Any] = {
        "n": int(len(durations)),
        "n_high": int(hi.sum()),
        "n_low": int(lo.sum()),
        "median_risk": median,
    }
    if hi.sum() > 0 and lo.sum() > 0:
        lr = stats.logrank_test(
            durations[hi], durations[lo], events[hi], events[lo]
        )
        result["logrank"] = {
            "statistic": float(lr.test_statistic),
            "p_value": float(lr.p_value),
            "significant_at_005": bool(lr.p_value < 0.05),
        }
    return result


run = skill_run(
    {
        "cox_cv_score": cox_cv_score,
        "km_auc_at_time": km_auc_at_time,
        "risk_groups": risk_groups,
    }
)

register_skill("survival_ml", run)
