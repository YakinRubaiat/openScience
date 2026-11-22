"""budget_optimization skill: allocate a capped budget (pure python).

Operations: ``allocate``, ``variance_report``.
"""

from __future__ import annotations

from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run


def allocate(requests: list, cap: float, strategy: str = "proportional",
             **kwargs: Any) -> dict[str, Any]:
    """Allocate a budget ``cap`` across funding ``requests``.

    ``requests``: ``[{"name": ..., "requested": amount, "priority"?: int}]``.
    ``strategy``: "proportional" (equal fraction of each request) or
    "greedy" (fully fund highest-priority first).
    """
    if not requests:
        raise ValueError("'requests' must be a non-empty list")
    cap = float(cap)
    if cap < 0:
        raise ValueError("cap must be >= 0")
    total_requested = sum(float(r["requested"]) for r in requests)
    if strategy == "proportional":
        frac = min(1.0, cap / total_requested) if total_requested else 0.0
        allocs = [{"name": r["name"], "requested": float(r["requested"]),
                   "allocated": round(float(r["requested"]) * frac, 2)}
                  for r in requests]
    elif strategy == "greedy":
        remaining = cap
        allocs = []
        for r in sorted(requests,
                        key=lambda x: int(x.get("priority", 999))):
            want = float(r["requested"])
            give = round(min(want, remaining), 2)
            remaining -= give
            allocs.append({"name": r["name"], "requested": want, "allocated": give})
    else:
        raise ValueError("strategy must be 'proportional' or 'greedy'")
    allocated_total = round(sum(a["allocated"] for a in allocs), 2)
    return {"status": "ok", "cap": cap, "total_requested": round(total_requested, 2),
            "total_allocated": allocated_total, "strategy": strategy,
            "allocations": allocs}


def variance_report(planned: dict | list, actual: dict | list,
                    **kwargs: Any) -> dict[str, Any]:
    """Variance (actual - planned) per item and overall.

    Accepts ``{name: amount}`` mappings or ``[{name, amount}]`` lists.
    """
    def norm(obj: Any, key: str) -> dict[str, float]:
        if isinstance(obj, dict):
            return {str(k): float(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return {str(i["name"]): float(i.get("amount", i.get(key, 0))) for i in obj}
        raise ValueError("provide dicts or lists of {name, amount}")

    p, a = norm(planned, "planned"), norm(actual, "actual")
    rows = []
    for name in sorted(set(p) | set(a)):
        pv, av = p.get(name, 0.0), a.get(name, 0.0)
        variance = av - pv
        rows.append({"name": name, "planned": pv, "actual": av,
                     "variance": round(variance, 2),
                     "variance_percent": round(100.0 * variance / pv, 2) if pv else None})
    return {"status": "ok",
            "total_planned": round(sum(p.values()), 2),
            "total_actual": round(sum(a.values()), 2),
            "total_variance": round(sum(a.values()) - sum(p.values()), 2),
            "items": rows}


run = skill_run({"allocate": allocate, "variance_report": variance_report})
register_skill("budget_optimization", run)
