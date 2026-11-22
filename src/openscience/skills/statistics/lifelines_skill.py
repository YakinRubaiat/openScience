"""Real lifelines-backed survival analysis skill: Kaplan-Meier, log-rank, Cox PH."""

from __future__ import annotations

from typing import Any

import numpy as np


def run(operation: str, **kwargs: Any) -> dict[str, Any]:
    if operation in ("kaplan_meier", "logrank", "survival"):
        return survival_analysis(**kwargs)
    if operation == "cox":
        return cox_ph(**kwargs)
    raise ValueError(f"Unknown lifelines operation: {operation}")


def _unwrap(kwargs: dict[str, Any]) -> dict[str, Any]:
    p = kwargs.get("parameters")
    return p if isinstance(p, dict) else kwargs


def survival_analysis(**kwargs: Any) -> dict[str, Any]:
    """Kaplan-Meier + log-rank comparing two groups labelled 0/1."""
    import pandas as pd
    from lifelines import KaplanMeierFitter
    from lifelines.statistics import logrank_test

    kw = _unwrap(kwargs)
    durations = np.asarray(kw["durations"], dtype=float)
    events = np.asarray(kw["events"], dtype=int)
    groups = np.asarray(kw["groups"])

    df = pd.DataFrame({"t": durations, "e": events, "g": groups})
    out: dict[str, Any] = {"test": "Kaplan-Meier + log-rank", "groups": {}}

    kmf = KaplanMeierFitter()
    ci_alpha = kw.get("ci_alpha", 0.05)
    for g in np.unique(groups):
        sub = df[df.g == g]
        kmf.fit(sub.t, sub.e, label=str(g), alpha=ci_alpha)
        t_grid = np.linspace(0, sub.t.max(), 41)
        surv = kmf.survival_function_at_times(t_grid).values
        out["groups"][str(g)] = {
            "n": len(sub),
            "events": int(sub.e.sum()),
            "median_survival": (
                float(kmf.median_survival_time_) if np.isfinite(kmf.median_survival_time_) else None
            ),
            "timeline": [float(t) for t in t_grid],
            "survival": [float(s) for s in surv],
        }

    gvals = np.unique(groups)
    if len(gvals) == 2:
        a = df[df.g == gvals[0]]
        b = df[df.g == gvals[1]]
        lr = logrank_test(a.t, b.t, a.e, b.e)
        out["logrank"] = {
            "statistic": float(lr.test_statistic),
            "p_value": float(lr.p_value),
            "significant_at_005": bool(lr.p_value < 0.05),
        }
    return out


def cox_ph(**kwargs: Any) -> dict[str, Any]:
    """Cox proportional-hazards model with covariates."""
    import pandas as pd
    from lifelines import CoxPHFitter

    kw = _unwrap(kwargs)
    df = pd.DataFrame(kw["dataframe"])
    cph = CoxPHFitter()
    cph.fit(df, duration_col=kw["duration_col"], event_col=kw["event_col"])
    s = cph.summary
    return {
        "test": "Cox proportional hazards",
        "n": int(df.shape[0]),
        "concordance": float(cph.concordance_index_),
        "log_likelihood": float(cph.log_likelihood_),
        "covariates": {
            str(idx): {
                "coef": float(row["coef"]),
                "hazard_ratio": float(np.exp(row["coef"])),
                "hr_ci95_lower": float(row["exp(coef) lower 95%"]),
                "hr_ci95_upper": float(row["exp(coef) upper 95%"]),
                "p_value": float(row["p"]),
                "significant_at_005": bool(row["p"] < 0.05),
            }
            for idx, row in s.iterrows()
        },
    }
