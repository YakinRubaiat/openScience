"""statsmodels_meta: fixed/random effects meta-analysis and forest-plot data."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import stats

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run


def _inputs(effect_sizes: Any, variances: Any | None, standard_errors: Any | None) -> tuple[np.ndarray, np.ndarray]:
    es = np.asarray(effect_sizes, dtype=float)
    if variances is not None:
        var = np.asarray(variances, dtype=float)
    elif standard_errors is not None:
        var = np.asarray(standard_errors, dtype=float) ** 2
    else:
        raise ValueError("Provide variances or standard_errors per study")
    if es.shape != var.shape:
        raise ValueError("effect_sizes and variances must have equal length")
    return es, var


def _alpha(kwargs: dict[str, Any]) -> float:
    return float(kwargs.get("alpha", 0.05))


def fixed_effect(effect_sizes: Any, variances: Any | None = None, standard_errors: Any | None = None, **kwargs: Any) -> dict[str, Any]:
    """Inverse-variance fixed-effect meta-analysis."""
    es, var = _inputs(effect_sizes, variances, standard_errors)
    weights = 1.0 / var
    pooled = float(np.sum(weights * es) / np.sum(weights))
    pooled_se = float(np.sqrt(1.0 / np.sum(weights)))
    z = stats.norm.ppf(1 - _alpha(kwargs) / 2)
    z_stat = pooled / pooled_se
    p = float(2 * (1 - stats.norm.cdf(abs(z_stat))))
    return result(
        model="fixed_effect_inverse_variance",
        n_studies=int(es.size),
        pooled_effect=pooled,
        pooled_se=pooled_se,
        ci_lower=pooled - z * pooled_se,
        ci_upper=pooled + z * pooled_se,
        z_statistic=float(z_stat),
        p_value=p,
        alpha=_alpha(kwargs),
    )


def random_effects(effect_sizes: Any, variances: Any | None = None, standard_errors: Any | None = None, **kwargs: Any) -> dict[str, Any]:
    """DerSimonian-Laird random-effects meta-analysis."""
    es, var = _inputs(effect_sizes, variances, standard_errors)
    k = es.size
    w = 1.0 / var
    fixed_pooled = np.sum(w * es) / np.sum(w)
    q = float(np.sum(w * (es - fixed_pooled) ** 2))
    c = float(np.sum(w) - np.sum(w**2) / np.sum(w))
    tau2 = max(0.0, (q - (k - 1)) / c) if c > 0 else 0.0
    w_re = 1.0 / (var + tau2)
    pooled = float(np.sum(w_re * es) / np.sum(w_re))
    pooled_se = float(np.sqrt(1.0 / np.sum(w_re)))
    z = stats.norm.ppf(1 - _alpha(kwargs) / 2)
    z_stat = pooled / pooled_se
    p = float(2 * (1 - stats.norm.cdf(abs(z_stat))))
    i2 = max(0.0, (q - (k - 1)) / q) if q > 0 else 0.0
    return result(
        model="random_effects_dersimonian_laird",
        n_studies=k,
        pooled_effect=pooled,
        pooled_se=pooled_se,
        ci_lower=pooled - z * pooled_se,
        ci_upper=pooled + z * pooled_se,
        z_statistic=float(z_stat),
        p_value=p,
        tau2=float(tau2),
        Q=q,
        I2=float(i2),
        alpha=_alpha(kwargs),
    )


def heterogeneity(effect_sizes: Any, variances: Any | None = None, standard_errors: Any | None = None, **kwargs: Any) -> dict[str, Any]:
    """Cochran's Q, I^2 and tau^2 (DerSimonian-Laird)."""
    es, var = _inputs(effect_sizes, variances, standard_errors)
    k = es.size
    w = 1.0 / var
    pooled = np.sum(w * es) / np.sum(w)
    q = float(np.sum(w * (es - pooled) ** 2))
    df = k - 1
    p = float(stats.chi2.sf(q, df)) if df > 0 else None
    i2 = max(0.0, (q - df) / q) if q > 0 else 0.0
    c = float(np.sum(w) - np.sum(w**2) / np.sum(w))
    tau2 = max(0.0, (q - df) / c) if c > 0 else 0.0
    return result(
        n_studies=k,
        Q=q,
        Q_df=int(df),
        Q_p_value=p,
        I2=float(i2),
        I2_percent=float(100 * i2),
        tau2=float(tau2),
    )


def forest_data(
    effect_sizes: Any,
    variances: Any | None = None,
    standard_errors: Any | None = None,
    study_labels: Any | None = None,
    model: str = "random",
    **kwargs: Any,
) -> dict[str, Any]:
    """Per-study effect sizes and CIs plus the pooled diamond, ready to plot."""
    es, var = _inputs(effect_sizes, variances, standard_errors)
    k = es.size
    z = stats.norm.ppf(1 - _alpha(kwargs) / 2)
    se = np.sqrt(var)
    labels = list(study_labels) if study_labels else [f"Study {i + 1}" for i in range(k)]
    if len(labels) != k:
        raise ValueError("study_labels must match number of studies")

    studies = [
        {
            "label": str(labels[i]),
            "effect": float(es[i]),
            "se": float(se[i]),
            "ci_lower": float(es[i] - z * se[i]),
            "ci_upper": float(es[i] + z * se[i]),
            "weight": float(1.0 / var[i]),
        }
        for i in range(k)
    ]
    pooled_out = random_effects(es, var, **kwargs) if model == "random" else fixed_effect(es, var, **kwargs)
    pooled = {
        "label": "Pooled (random effects)" if model == "random" else "Pooled (fixed effect)",
        "effect": pooled_out["pooled_effect"],
        "ci_lower": pooled_out["ci_lower"],
        "ci_upper": pooled_out["ci_upper"],
        "p_value": pooled_out["p_value"],
    }
    return result(
        model=pooled_out["model"],
        n_studies=k,
        alpha=_alpha(kwargs),
        studies=studies,
        pooled=pooled,
    )


run = skill_run(
    {
        "fixed_effect": fixed_effect,
        "random_effects": random_effects,
        "heterogeneity": heterogeneity,
        "forest_data": forest_data,
    }
)

register_skill("statsmodels_meta", run)
