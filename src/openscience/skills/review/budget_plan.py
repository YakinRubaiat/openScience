"""budget_planning skill: quarterly budget plans and forecasts (pure python).

Operations: ``year_plan``, ``burn_rate``, ``forecast_eoy``.
"""

from __future__ import annotations

from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run

QUARTERS = ("Q1", "Q2", "Q3", "Q4")


def year_plan(total_budget: float, weights: list | None = None,
              carryover: float = 0.0, **kwargs: Any) -> dict[str, Any]:
    """Split an annual budget across quarters.

    ``weights``: optional 4 quarter weights (default equal). ``carryover``
    is added to the available budget before splitting.
    """
    total = float(total_budget) + float(carryover)
    if total < 0:
        raise ValueError("budget must be >= 0")
    if weights is None:
        weights = [1.0, 1.0, 1.0, 1.0]
    weights = [float(w) for w in weights]
    if len(weights) != 4 or any(w < 0 for w in weights) or sum(weights) <= 0:
        raise ValueError("'weights' must be 4 non-negative numbers summing > 0")
    scale = total / sum(weights)
    quarters = {q: round(w * scale, 2) for q, w in zip(QUARTERS, weights)}
    return {"status": "ok", "year_budget": round(total, 2),
            "carryover": float(carryover), "quarters": quarters}


def burn_rate(spent: float, elapsed_weeks: float, **kwargs: Any) -> dict[str, Any]:
    """Weekly burn rate from spend so far."""
    spent = float(spent)
    elapsed = float(elapsed_weeks)
    if elapsed <= 0:
        raise ValueError("elapsed_weeks must be > 0")
    return {"status": "ok", "spent": spent, "elapsed_weeks": elapsed,
            "burn_rate_per_week": round(spent / elapsed, 2)}


def forecast_eoy(total_budget: float, spent: float, elapsed_weeks: float,
                 year_weeks: float = 52.0, **kwargs: Any) -> dict[str, Any]:
    """Forecast end-of-year spend at the current burn rate.

    EOY spend = spent + burn_rate * remaining weeks; compares to budget.
    """
    rate = burn_rate(spent, elapsed_weeks)["burn_rate_per_week"]
    remaining = max(0.0, float(year_weeks) - float(elapsed_weeks))
    forecast = float(spent) + rate * remaining
    variance = float(total_budget) - forecast
    return {"status": "ok", "total_budget": float(total_budget),
            "spent": float(spent), "elapsed_weeks": float(elapsed_weeks),
            "burn_rate_per_week": rate,
            "forecast_eoy_spend": round(forecast, 2),
            "forecast_variance": round(variance, 2),
            "on_track": variance >= 0}


run = skill_run({"year_plan": year_plan, "burn_rate": burn_rate,
                 "forecast_eoy": forecast_eoy})
register_skill("budget_planning", run)
