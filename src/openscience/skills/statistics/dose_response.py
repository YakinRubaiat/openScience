"""Dose-response analysis skill: Hill-fit IC50/EC50 and per-compound tables."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import optimize

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run


def _hill(x: np.ndarray, bottom: float, top: float, ec50: float, hill_n: float) -> np.ndarray:
    return bottom + (top - bottom) / (1.0 + (ec50 / x) ** hill_n)


def _fit_hill(xv: np.ndarray, yv: np.ndarray) -> tuple[np.ndarray, float]:
    p0 = [float(yv.min()), float(yv.max()), float(np.median(xv[xv > 0]) if (xv > 0).any() else 1.0), 1.0]
    popt, _ = optimize.curve_fit(_hill, xv, yv, p0=p0, maxfev=20000)
    yhat = _hill(xv, *popt)
    ss_res = float(np.sum((yv - yhat) ** 2))
    ss_tot = float(np.sum((yv - yv.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return popt, r2


def fit_drc(dose: Any, response: Any, **kwargs: Any) -> dict[str, Any]:
    """Fit a 4-parameter Hill dose-response curve.

    Response convention: decreasing curves give EC50 = IC50. Returns the
    fitted parameters, fitted curve values and R^2.
    """
    xv = np.asarray(dose, dtype=float)
    yv = np.asarray(response, dtype=float)
    popt, r2 = _fit_hill(xv, yv)
    bottom, top, ec50, hill_n = (float(v) for v in popt)
    return result(
        model="hill_drc",
        bottom=bottom,
        top=top,
        EC50=ec50,
        IC50=ec50 if top > bottom else None,
        hill_n=hill_n,
        r_squared=r2,
        n=int(xv.size),
        fitted=_hill(xv, *popt).tolist(),
    )


def ic50(dose: Any, response: Any, **kwargs: Any) -> dict[str, Any]:
    """IC50 via Hill fit, with a linear-interpolation fallback."""
    xv = np.asarray(dose, dtype=float)
    yv = np.asarray(response, dtype=float)
    try:
        popt, r2 = _fit_hill(xv, yv)
        bottom, top, ec50, hill_n = (float(v) for v in popt)
        method = "hill_fit"
    except Exception:  # noqa: BLE001 - fall back to interpolation at halfway point
        order = np.argsort(xv)
        xs, ys = xv[order], yv[order]
        half = (ys.max() + ys.min()) / 2.0
        # np.interp needs ascending xp; flip if the response increases with dose
        if ys[-1] >= ys[0]:
            ec50 = float(np.interp(half, ys, xs))
        else:
            ec50 = float(np.interp(half, ys[::-1], xs[::-1]))
        bottom, top, hill_n, r2, method = float(yv.min()), float(yv.max()), None, None, "interpolation"
    return result(
        IC50=float(ec50),
        EC50=float(ec50),
        bottom=float(bottom),
        top=float(top),
        hill_n=hill_n,
        r_squared=r2,
        method=method,
        n=int(xv.size),
    )


def summarize_table(records: Any, **kwargs: Any) -> dict[str, Any]:
    """Per-compound dose-response metrics from a list of records.

    Each record: {"compound": str, "dose": float, "response": float}.
    Fits one Hill curve per compound and returns metrics per compound.
    """
    import pandas as pd

    df = pd.DataFrame(records)
    required = {"compound", "dose", "response"}
    if not required.issubset(df.columns):
        raise ValueError(f"records need columns {sorted(required)}")

    compounds = []
    for compound, grp in df.groupby("compound"):
        xv = grp["dose"].to_numpy(dtype=float)
        yv = grp["response"].to_numpy(dtype=float)
        entry: dict[str, Any] = {"compound": compound, "n_points": int(len(grp)),
                                 "min_response": float(yv.min()), "max_response": float(yv.max())}
        try:
            popt, r2 = _fit_hill(xv, yv)
            bottom, top, ec50, hill_n = (float(v) for v in popt)
            entry.update(IC50=ec50, EC50=ec50, bottom=bottom, top=top,
                         hill_n=hill_n, r_squared=r2, fit_ok=True)
        except Exception:  # noqa: BLE001 - too few points or degenerate curve
            entry.update(fit_ok=False)
        compounds.append(entry)

    return result(n_compounds=len(compounds), compounds=compounds)


run = skill_run(
    {
        "fit_drc": fit_drc,
        "ic50": ic50,
        "summarize_table": summarize_table,
    }
)

register_skill("dose_response_analysis", run)
