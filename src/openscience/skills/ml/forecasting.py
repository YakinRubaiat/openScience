"""Forecasting skill: simple, dependency-light time-series forecasting.

Distinct from the statistics agent's ``time_series_design`` (experimental
design for time-series experiments); this skill provides lightweight
forecasting baselines.

Operations
----------
- ``naive_forecast``          — last-value and seasonal-naive baselines
- ``moving_average_forecast`` — rolling mean / exponential smoothing
- ``linear_trend_forecast``   — least-squares linear trend extrapolation
- ``forecast_metrics``        — MAE/RMSE/MAPE (zero-guarded) between forecast
  and actual values
"""

from __future__ import annotations

from typing import Any

import numpy as np

from openscience.skills import register_skill
from openscience.skills._common import skill_run, unwrap


def _get_series(kw: dict[str, Any]) -> np.ndarray:
    if "series" in kw:
        return np.asarray(kw["series"], dtype=float)
    if "values" in kw:
        return np.asarray(kw["values"], dtype=float)
    raise ValueError("Provide 'series' (1-D array of values)")


def naive_forecast(**kwargs: Any) -> dict[str, Any]:
    """Naive / seasonal-naive forecast.

    Parameters: ``series``, ``horizon`` (default 1), ``season_length``
    (optional — uses the value ``season_length`` steps back).
    """
    kw = unwrap(kwargs)
    y = _get_series(kw)
    horizon = int(kw.get("horizon", 1))
    if y.shape[0] < 1:
        raise ValueError("series must contain at least one value")
    season = kw.get("season_length")

    if season is None:
        last = float(y[-1])
        point = np.full(horizon, last)
    else:
        season = int(season)
        if season < 1 or y.shape[0] < season:
            raise ValueError("season_length must be >= 1 and <= len(series)")
        reps = int(np.ceil(horizon / season))
        tile = np.tile(y[-season:], reps)
        point = tile[:horizon].astype(float)

    return {
        "horizon": horizon,
        "season_length": season,
        "forecast": point.tolist(),
    }


def moving_average_forecast(**kwargs: Any) -> dict[str, Any]:
    """Moving-average or simple exponential-smoothing forecast.

    Parameters: ``series``, ``horizon`` (default 1), ``window`` (default 3)
    for moving average, or ``method="exp"`` with ``alpha`` (default 0.5).
    """
    kw = unwrap(kwargs)
    y = _get_series(kw)
    horizon = int(kw.get("horizon", 1))
    method = kw.get("method", "sma")
    if y.shape[0] < 1:
        raise ValueError("series must contain at least one value")

    if method == "sma":
        window = int(kw.get("window", 3))
        window = max(1, min(window, y.shape[0]))
        value = float(np.mean(y[-window:]))
        params: dict[str, Any] = {"window": window}
    elif method == "exp":
        alpha = float(kw.get("alpha", 0.5))
        if not (0.0 < alpha <= 1.0):
            raise ValueError("alpha must be in (0, 1]")
        value = float(y[0])
        for v in y[1:]:
            value = alpha * float(v) + (1.0 - alpha) * value
        params = {"alpha": alpha}
    else:
        raise ValueError("method must be 'sma' or 'exp'")

    forecast = np.full(horizon, value)
    return {
        "horizon": horizon,
        "method": method,
        "params": params,
        "forecast": forecast.tolist(),
    }


def linear_trend_forecast(**kwargs: Any) -> dict[str, Any]:
    """Least-squares linear trend extrapolation.

    Parameters: ``series``, ``horizon`` (default 1).
    """
    kw = unwrap(kwargs)
    y = _get_series(kw)
    horizon = int(kw.get("horizon", 1))
    n = y.shape[0]
    if n < 2:
        raise ValueError("series must contain at least 2 values")

    t = np.arange(n, dtype=float)
    slope, intercept = np.polyfit(t, y, 1)
    future_t = np.arange(n, n + horizon, dtype=float)
    forecast = intercept + slope * future_t

    return {
        "horizon": horizon,
        "slope": float(slope),
        "intercept": float(intercept),
        "forecast": forecast.tolist(),
    }


def forecast_metrics(**kwargs: Any) -> dict[str, Any]:
    """MAE/RMSE/MAPE between ``y_true`` and ``y_pred`` (MAPE zero-guarded)."""
    kw = unwrap(kwargs)
    y_true = np.asarray(kw["y_true"], dtype=float)
    y_pred = np.asarray(kw["y_pred"], dtype=float)
    if y_true.shape != y_pred.shape:
        raise ValueError("y_true and y_pred must have the same shape")
    eps = float(kw.get("eps", 1e-8))

    n = y_true.shape[0]
    err = y_true - y_pred
    mae = float(np.mean(np.abs(err))) if n else None
    rmse = float(np.sqrt(np.mean(err**2))) if n else None
    nonzero = np.abs(y_true) > eps
    mape = (
        float(np.mean(np.abs(err[nonzero] / y_true[nonzero])) * 100.0)
        if nonzero.any()
        else None
    )
    return {"n": int(n), "mae": mae, "rmse": rmse, "mape_percent": mape}


run = skill_run(
    {
        "naive_forecast": naive_forecast,
        "moving_average_forecast": moving_average_forecast,
        "linear_trend_forecast": linear_trend_forecast,
        "forecast_metrics": forecast_metrics,
    }
)

register_skill("forecasting", run)
