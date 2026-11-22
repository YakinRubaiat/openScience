"""Pure-numpy/scipy descriptive statistics skill."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import stats

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run


def descriptive(data: Any, **kwargs: Any) -> dict[str, Any]:
    """Mean, std, percentiles of a numeric array."""
    x = np.asarray(data, dtype=float)
    percentiles = kwargs.get("percentiles", [25, 50, 75])
    return result(
        n=int(x.size),
        mean=float(np.mean(x)),
        std=float(np.std(x, ddof=1)),
        min=float(np.min(x)),
        max=float(np.max(x)),
        sum=float(np.sum(x)),
        percentiles={str(p): float(np.percentile(x, p)) for p in percentiles},
    )


def ttest_1samp(data: Any, popmean: float = 0.0, **kwargs: Any) -> dict[str, Any]:
    """One-sample t-test against a population mean."""
    x = np.asarray(data, dtype=float)
    t, p = stats.ttest_1samp(x, popmean)
    return result(
        test="one-sample t-test",
        n=int(x.size),
        sample_mean=float(np.mean(x)),
        popmean=float(popmean),
        t_statistic=float(t),
        df=int(x.size - 1),
        p_value=float(p),
        significant_at_005=bool(p < 0.05),
    )


def correlation(x: Any, y: Any, method: str = "pearson", **kwargs: Any) -> dict[str, Any]:
    """Pearson or Spearman correlation between two arrays."""
    a = np.asarray(x, dtype=float)
    b = np.asarray(y, dtype=float)
    if method == "spearman":
        r, p = stats.spearmanr(a, b)
    else:
        r, p = stats.pearsonr(a, b)
        method = "pearson"
    return result(
        test=f"{method} correlation",
        n=int(a.size),
        method=method,
        r=float(r),
        p_value=float(p),
        significant_at_005=bool(p < 0.05),
    )


def regression_slope(x: Any, y: Any, **kwargs: Any) -> dict[str, Any]:
    """Simple linear regression slope/intercept via least squares."""
    a = np.asarray(x, dtype=float)
    b = np.asarray(y, dtype=float)
    res = stats.linregress(a, b)
    return result(
        test="simple linear regression",
        n=int(a.size),
        slope=float(res.slope),
        intercept=float(res.intercept),
        r_value=float(res.rvalue),
        r_squared=float(res.rvalue**2),
        slope_stderr=float(res.stderr),
        intercept_stderr=float(res.intercept_stderr),
        p_value=float(res.pvalue),
    )


run = skill_run(
    {
        "descriptive": descriptive,
        "ttest_1samp": ttest_1samp,
        "correlation": correlation,
        "regression_slope": regression_slope,
    }
)

register_skill("numpy_stats", run)
