"""cost_modeling skill: resource cost estimation (pure python).

Operations: ``estimate``, ``breakdown_by_category``, ``contingency``.
"""

from __future__ import annotations

from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run


def _LineItem(resource: dict[str, Any]) -> dict[str, Any]:
    hours = float(resource.get("hours", 0))
    rate = float(resource.get("rate", 0))
    cost = hours * rate
    return {"name": resource.get("name", resource.get("role", "resource")),
            "category": resource.get("category", "labor"),
            "hours": hours, "rate": rate, "cost": cost}


def estimate(resources: list, **kwargs: Any) -> dict[str, Any]:
    """Total cost = sum(hours * rate) over ``resources``."""
    if not isinstance(resources, list) or not resources:
        raise ValueError("'resources' must be a non-empty list of {hours, rate} dicts")
    items = [_LineItem(r) for r in resources]
    total = sum(i["cost"] for i in items)
    return {"status": "ok", "n_items": len(items), "total_cost": round(total, 2),
            "items": items}


def breakdown_by_category(resources: list, **kwargs: Any) -> dict[str, Any]:
    """Cost subtotals per category plus the grand total."""
    est = estimate(resources)
    by_cat: dict[str, float] = {}
    hours_by_cat: dict[str, float] = {}
    for item in est["items"]:
        by_cat[item["category"]] = by_cat.get(item["category"], 0.0) + item["cost"]
        hours_by_cat[item["category"]] = (hours_by_cat.get(item["category"], 0.0)
                                          + item["hours"])
    breakdown = {c: {"cost": round(by_cat[c], 2),
                     "hours": hours_by_cat[c],
                     "share_percent": round(100.0 * by_cat[c] / est["total_cost"], 2)
                     if est["total_cost"] else 0.0}
                 for c in sorted(by_cat)}
    return {"status": "ok", "total_cost": est["total_cost"], "by_category": breakdown}


def contingency(total: float | None = None, resources: list | None = None,
                percent: float = 10.0, **kwargs: Any) -> dict[str, Any]:
    """Contingency reserve: ``percent`` of the base cost."""
    if total is None:
        if resources is None:
            raise ValueError("Provide 'total' or 'resources'")
        total = estimate(resources)["total_cost"]
    total = float(total)
    reserve = total * float(percent) / 100.0
    return {"status": "ok", "base_cost": round(total, 2),
            "percent": float(percent),
            "contingency": round(reserve, 2),
            "total_with_contingency": round(total + reserve, 2)}


run = skill_run({"estimate": estimate, "breakdown_by_category": breakdown_by_category,
                 "contingency": contingency})
register_skill("cost_modeling", run)
