"""Curve fitting skill: Hill equation, 4PL and linear fits via scipy."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import optimize

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run


def _hill(x: np.ndarray, bottom: float, top: float, ec50: float, hill_n: float) -> np.ndarray:
    return bottom + (top - bottom) / (1.0 + (ec50 / x) ** hill_n)


def _four_pl(x: np.ndarray, a: float, b: float, c: float, d: float) -> np.ndarray:
    # a: bottom, b: hill slope, c: inflection (EC50), d: top
    return d + (a - d) / (1.0 + (x / c) ** b)


def _r2(y: np.ndarray, yhat: np.ndarray) -> float:
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0


def hill_equation(
    x: Any,
    y: Any,
    p0: Any | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Fit the Hill equation: y = bottom + (top-bottom)/(1 + (EC50/x)^n).

    Returns EC50, Emax (top), bottom, Hill coefficient, and R^2.
    """
    xv = np.asarray(x, dtype=float)
    yv = np.asarray(y, dtype=float)
    if p0 is None:
        p0 = [yv.min(), yv.max(), float(np.median(xv)), 1.0]
    popt, pcov = optimize.curve_fit(_hill, xv, yv, p0=p0, maxfev=20000)
    bottom, top, ec50, hill_n = (float(v) for v in popt)
    yhat = _hill(xv, *popt)
    perr = np.sqrt(np.diag(pcov)) if pcov.size else np.full(4, np.nan)
    return result(
        model="hill_equation",
        bottom=bottom,
        Emax=top,
        EC50=ec50,
        hill_n=hill_n,
        EC50_stderr=float(perr[2]),
        r_squared=_r2(yv, yhat),
        n=int(xv.size),
    )


def four_pl(x: Any, y: Any, p0: Any | None = None, **kwargs: Any) -> dict[str, Any]:
    """Four-parameter logistic: y = d + (a-d)/(1 + (x/c)^b)."""
    xv = np.asarray(x, dtype=float)
    yv = np.asarray(y, dtype=float)
    if p0 is None:
        p0 = [yv.min(), 1.0, float(np.median(xv)), yv.max()]
    popt, pcov = optimize.curve_fit(_four_pl, xv, yv, p0=p0, maxfev=20000)
    a, b, c, d = (float(v) for v in popt)
    yhat = _four_pl(xv, *popt)
    return result(
        model="four_parameter_logistic",
        bottom=a,
        hill_slope=b,
        EC50=c,
        top=d,
        r_squared=_r2(yv, yhat),
        n=int(xv.size),
    )


def linear_fit(x: Any, y: Any, **kwargs: Any) -> dict[str, Any]:
    """Least-squares straight-line fit y = slope*x + intercept."""
    xv = np.asarray(x, dtype=float)
    yv = np.asarray(y, dtype=float)
    coeffs = np.polyfit(xv, yv, 1)
    slope, intercept = float(coeffs[0]), float(coeffs[1])
    yhat = slope * xv + intercept
    return result(
        model="linear",
        slope=slope,
        intercept=intercept,
        r_squared=_r2(yv, yhat),
        n=int(xv.size),
    )


def goodness(y: Any, yhat: Any, **kwargs: Any) -> dict[str, Any]:
    """Goodness-of-fit metrics: R^2, adjusted R^2, RMSE."""
    yv = np.asarray(y, dtype=float)
    yh = np.asarray(yhat, dtype=float)
    n = int(yv.size)
    r2 = _r2(yv, yh)
    k = int(kwargs.get("n_params", 2))
    adj = 1.0 - (1.0 - r2) * (n - 1) / max(n - k - 1, 1)
    rmse = float(np.sqrt(np.mean((yv - yh) ** 2)))
    return result(r_squared=r2, adj_r_squared=adj, rmse=rmse, n=n)


run = skill_run(
    {
        "hill_equation": hill_equation,
        "four_pl": four_pl,
        "linear_fit": linear_fit,
        "goodness": goodness,
    }
)

register_skill("curve_fitting", run)
