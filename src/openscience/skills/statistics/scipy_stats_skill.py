"""Real scipy.stats-backed skill: descriptive stats and non-parametric tests."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import stats


def run(operation: str, **kwargs: Any) -> dict[str, Any]:
    if operation == "describe":
        return describe(**kwargs)
    if operation == "mannwhitney":
        return mannwhitney(**kwargs)
    if operation == "shapiro":
        return shapiro(**kwargs)
    raise ValueError(f"Unknown scipy_stats operation: {operation}")


def _unwrap(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Agents pass parameters={"parameters": {...}}; unwrap one level."""
    p = kwargs.get("parameters")
    return p if isinstance(p, dict) else kwargs


def describe(data: Any = None, **kwargs: Any) -> dict[str, Any]:
    data = np.asarray(data if data is not None else _unwrap(kwargs).get("data"), dtype=float)
    res = stats.describe(data)
    return {
        "n": int(res.nobs),
        "mean": float(res.mean),
        "variance": float(res.variance),
        "sd": float(np.sqrt(res.variance)),
        "min": float(res.minmax[0]),
        "max": float(res.minmax[1]),
        "skewness": float(res.skewness),
        "kurtosis": float(res.kurtosis),
        "median": float(np.median(data)),
        "q25": float(np.percentile(data, 25)),
        "q75": float(np.percentile(data, 75)),
    }


def mannwhitney(group1: Any = None, group2: Any = None, **kwargs: Any) -> dict[str, Any]:
    kw = _unwrap(kwargs)
    g1 = np.asarray(group1 if group1 is not None else kw["group1"], dtype=float)
    g2 = np.asarray(group2 if group2 is not None else kw["group2"], dtype=float)
    u, p = stats.mannwhitneyu(g1, g2, alternative="two-sided")
    # rank-biserial correlation as effect size
    rbc = 1 - (2 * u) / (len(g1) * len(g2))
    return {
        "test": "Mann-Whitney U",
        "u_statistic": float(u),
        "p_value": float(p),
        "rank_biserial_r": float(rbc),
        "n1": len(g1),
        "n2": len(g2),
        "significant_at_005": bool(p < 0.05),
    }


def shapiro(data: Any = None, **kwargs: Any) -> dict[str, Any]:
    data = np.asarray(data if data is not None else _unwrap(kwargs).get("data"), dtype=float)
    w, p = stats.shapiro(data)
    return {
        "test": "Shapiro-Wilk normality",
        "w_statistic": float(w),
        "p_value": float(p),
        "normal_at_005": bool(p >= 0.05),
    }
