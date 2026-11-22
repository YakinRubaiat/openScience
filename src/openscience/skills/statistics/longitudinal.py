"""Longitudinal analysis: linear mixed models and per-subject summaries."""

from __future__ import annotations

from typing import Any

import numpy as np

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run


def lmm(
    subject: Any | None = None,
    time: Any | None = None,
    y: Any | None = None,
    group: Any | None = None,
    records: Any | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Linear mixed model y ~ time (+ group), random intercept per subject.

    Accepts either array args (subject/time/y[/group]) or ``records`` — a
    list of dicts with keys subject/time/y[/group].
    """
    import pandas as pd
    import statsmodels.formula.api as smf

    if records is not None:
        df = pd.DataFrame(records)
    else:
        cols: dict[str, Any] = {}
        if subject is None or time is None or y is None:
            raise ValueError("lmm requires records or (subject, time, y) arrays")
        cols["subject"] = list(subject)
        cols["time"] = np.asarray(time, dtype=float)
        cols["y"] = np.asarray(y, dtype=float)
        if group is not None:
            cols["group"] = list(group)
        df = pd.DataFrame(cols)

    df["time"] = df["time"].astype(float)
    df["y"] = df["y"].astype(float)
    for col in ("subject", "group"):
        if col in df.columns:
            df[col] = df[col].astype(str)

    formula = "y ~ time" + (" + group" if "group" in df.columns else "")
    model = smf.mixedlm(formula, df, groups=df["subject"])
    fit = model.fit(reml=False, method="lbfgs")

    params = {str(k): float(v) for k, v in fit.params.items()}
    pvalues = {str(k): float(v) for k, v in fit.pvalues.items()}
    bse = {str(k): float(v) for k, v in fit.bse.items()}
    return result(
        model="linear_mixed_effects",
        formula=formula,
        n_obs=int(fit.nobs),
        n_groups=int(len(df["subject"].unique())),
        log_likelihood=float(fit.llf),
        fixed_effects={k: {"coef": params[k], "std_err": bse[k], "p_value": pvalues[k]}
                       for k in params if k != "Group Var"},
        random_effects_var=float(fit.cov_re.iloc[0, 0]),
        converged=bool(fit.converged),
    )


def _records(subject: Any, time: Any, y: Any) -> list[tuple]:
    subj = list(subject)
    tv = np.asarray(time, dtype=float)
    yv = np.asarray(y, dtype=float)
    return sorted(zip(subj, tv, yv), key=lambda r: (str(r[0]), r[1]))


def auc_per_subject(subject: Any, time: Any, y: Any, **kwargs: Any) -> dict[str, Any]:
    """Trapezoidal AUC per subject over time."""
    aucs: dict[str, float] = {}
    times: dict[str, list] = {}
    vals: dict[str, list] = {}
    for s, t, v in _records(subject, time, y):
        times.setdefault(str(s), []).append(t)
        vals.setdefault(str(s), []).append(v)
    for s in times:
        aucs[s] = float(np.trapezoid(vals[s], times[s])) if len(times[s]) > 1 else 0.0
    return result(n_subjects=len(aucs), auc_per_subject=aucs)


def slope_per_subject(subject: Any, time: Any, y: Any, **kwargs: Any) -> dict[str, Any]:
    """Per-subject least-squares slope of y on time."""
    times: dict[str, list] = {}
    vals: dict[str, list] = {}
    for s, t, v in _records(subject, time, y):
        times.setdefault(str(s), []).append(t)
        vals.setdefault(str(s), []).append(v)
    slopes: dict[str, float] = {}
    for s in times:
        t, v = np.asarray(times[s]), np.asarray(vals[s])
        if len(t) > 1 and np.ptp(t) > 0:
            slopes[s] = float(np.polyfit(t, v, 1)[0])
        else:
            slopes[s] = 0.0
    return result(n_subjects=len(slopes), slope_per_subject=slopes)


run = skill_run(
    {
        "lmm": lmm,
        "auc_per_subject": auc_per_subject,
        "slope_per_subject": slope_per_subject,
    }
)

register_skill("longitudinal_analysis", run)
