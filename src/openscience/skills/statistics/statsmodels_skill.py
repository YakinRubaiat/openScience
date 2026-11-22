"""Real statsmodels-backed skill for openScience agents.

Operations
----------
- ``power_analysis``: two-sample t-test sample size via TTestIndPower
- ``ttest``: OLS-based two-sample t-test (Welch or Student)
- ``ols``: ordinary least squares with covariates
"""

from __future__ import annotations

from typing import Any

import numpy as np


def run(operation: str, **kwargs: Any) -> dict[str, Any]:
    """Dispatch a statsmodels operation."""
    if operation == "power_analysis":
        return power_analysis(**kwargs)
    if operation == "ttest":
        return ttest(**kwargs)
    if operation == "ols":
        return ols(**kwargs)
    raise ValueError(f"Unknown statsmodels operation: {operation}")


def power_analysis(
    effect_size: float = 0.5,
    alpha: float = 0.05,
    power: float = 0.8,
    alternative: str = "two-sided",
    ratio: float = 1.0,
    **_ignored: Any,
) -> dict[str, Any]:
    """Compute required sample size per group for a two-sample t-test.

    Also returns a small power curve (n vs achieved power) so the agent's
    advertised ``power_curve`` output type is real.
    """
    from statsmodels.stats.power import TTestIndPower

    solver = TTestIndPower()
    n_per_group = solver.solve_power(
        effect_size=effect_size,
        alpha=alpha,
        power=power,
        ratio=ratio,
        alternative=alternative,
    )

    # Power curve over a range of n's (useful for reports/plots).
    n_grid = np.unique(
        np.clip(
            np.round(np.linspace(n_per_group * 0.25, n_per_group * 1.75, 8)).astype(int),
            2,
            None,
        )
    )
    curve = [
        {
            "n_per_group": int(n),
            "power": float(
                solver.power(
                    effect_size=effect_size,
                    nobs1=int(n),
                    alpha=alpha,
                    ratio=ratio,
                    alternative=alternative,
                )
            ),
        }
        for n in n_grid
    ]

    return {
        "test": "two-sample t-test",
        "effect_size": float(effect_size),
        "effect_metric": "Cohen's d",
        "alpha": float(alpha),
        "power_target": float(power),
        "alternative": alternative,
        "ratio": float(ratio),
        "n_per_group": int(np.ceil(n_per_group)),
        "n_total": int(np.ceil(n_per_group) * (1 + ratio)),
        "power_curve": curve,
    }


def ttest(
    group1: Any,
    group2: Any = None,
    equal_var: bool = False,
    alpha: float = 0.05,
    **kwargs: Any,
) -> dict[str, Any]:
    """Two-group comparison using statsmodels' CompareMeans.

    Accepts raw arrays (``group1``/``group2``) or a ``parameters`` wrapper
    containing ``group1``/``group2`` (agents pass parameters through).
    """
    from scipy import stats as sp_stats
    from statsmodels.stats.weightstats import CompareMeans, DescrStatsW

    if isinstance(group1, dict) and "group1" in group1:  # un-wrap parameters dict
        inner = group1
        group1 = inner["group1"]
        group2 = inner.get("group2")
        equal_var = inner.get("equal_var", equal_var)
        alpha = inner.get("alpha", alpha)

    if group2 is None:
        raise ValueError("ttest requires group1 and group2 arrays")

    g1, g2 = np.asarray(group1, dtype=float), np.asarray(group2, dtype=float)
    cm = CompareMeans(DescrStatsW(g1), DescrStatsW(g2))
    tstat, pval, df = cm.ttest_ind(alternative="two-sided", usevar="unequal" if not equal_var else "pooled")

    # Effect sizes
    m1, m2 = g1.mean(), g2.mean()
    s1, s2 = g1.std(ddof=1), g2.std(ddof=1)
    pooled_sd = np.sqrt(((len(g1) - 1) * s1**2 + (len(g2) - 1) * s2**2) / (len(g1) + len(g2) - 2))
    cohens_d = (m2 - m1) / pooled_sd
    # Hedges' g correction
    J = 1 - 3 / (4 * (len(g1) + len(g2)) - 9)
    hedges_g = cohens_d * J

    mean_diff_ci = cm.tconfint_diff(alpha=alpha, usevar="unequal" if not equal_var else "pooled")

    return {
        "test": "Welch t-test" if not equal_var else "Student t-test",
        "n1": int(len(g1)),
        "n2": int(len(g2)),
        "mean_group1": float(m1),
        "mean_group2": float(m2),
        "sd_group1": float(s1),
        "sd_group2": float(s2),
        "mean_diff": float(m2 - m1),
        "mean_diff_ci95": [float(mean_diff_ci[0]), float(mean_diff_ci[1])],
        "t_statistic": float(tstat),
        "p_value": float(pval),
        "df": float(df),
        "cohens_d": float(cohens_d),
        "hedges_g": float(hedges_g),
        "significant_at_005": bool(pval < 0.05),
        # Backwards-compat for power_analysisagent passthrough
        "effect_size": kwargs.get("effect_size"),
        "alpha_": float(alpha),
    }


def ols(y: Any, X: Any, feature_names: Any = None, **kwargs: Any) -> dict[str, Any]:
    """Fit OLS regression."""
    import statsmodels.api as sm

    if isinstance(y, dict) and "y" in y:
        inner = y
        y, X, feature_names = inner["y"], inner["X"], inner.get("feature_names")

    y = np.asarray(y, dtype=float)
    X = np.asarray(X, dtype=float)
    if X.ndim == 1:
        X = X.reshape(-1, 1)
    Xd = sm.add_constant(X)
    names = ["const"] + (feature_names or [f"x{i+1}" for i in range(X.shape[1])])
    model = sm.OLS(y, Xd).fit()

    return {
        "test": "OLS regression",
        "n": int(len(y)),
        "r_squared": float(model.rsquared),
        "adj_r_squared": float(model.rsquared_adj),
        "f_statistic": float(model.fvalue),
        "f_p_value": float(model.f_pvalue),
        "coefficients": {
            name: {
                "coef": float(model.params[i]),
                "std_err": float(model.bse[i]),
                "t": float(model.tvalues[i]),
                "p_value": float(model.pvalues[i]),
                "ci95": [float(model.conf_int()[i, 0]), float(model.conf_int()[i, 1])],
            }
            for i, name in enumerate(names)
        },
    }
