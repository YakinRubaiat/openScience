"""resource_planning skill: FTE estimates, allocation conflicts, gantt data.

Operations: ``fte_estimate``, ``timeline_conflict``, ``gantt_data``.
"""

from __future__ import annotations

from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run

HOURS_PER_FTE_WEEK = 40.0


def fte_estimate(tasks: list, hours_per_fte_week: float = HOURS_PER_FTE_WEEK,
                 **kwargs: Any) -> dict[str, Any]:
    """FTE-weeks needed for ``tasks`` (each ``{name, hours[, assignee]}``)."""
    if not tasks:
        raise ValueError("'tasks' must be a non-empty list of {name, hours} dicts")
    total = 0.0
    per_role: dict[str, float] = {}
    for t in tasks:
        hours = float(t.get("hours", 0) or 0)
        total += hours
        role = t.get("role", t.get("assignee", "unassigned"))
        per_role[role] = per_role.get(role, 0.0) + hours
    fte_weeks = total / float(hours_per_fte_week)
    return {"status": "ok", "n_tasks": len(tasks), "total_hours": total,
            "fte_weeks": round(fte_weeks, 2),
            "by_role": {r: {"hours": h, "fte_weeks": round(h / float(hours_per_fte_week), 2)}
                        for r, h in sorted(per_role.items())}}


def _overlaps(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return int(a["start"]) < int(b["end"]) and int(b["start"]) < int(a["end"])


def timeline_conflict(allocations: list, **kwargs: Any) -> dict[str, Any]:
    """Overlapping allocations per resource.

    ``allocations``: ``{resource, task, start, end}`` (week/day indices;
    ``end`` exclusive).
    """
    conflicts = []
    by_resource: dict[str, list[dict[str, Any]]] = {}
    for a in allocations:
        for k in ("resource", "task", "start", "end"):
            if k not in a:
                raise ValueError(f"allocation missing {k!r}: {a}")
        by_resource.setdefault(str(a["resource"]), []).append(a)
    for resource, allocs in sorted(by_resource.items()):
        ordered = sorted(allocs, key=lambda a: int(a["start"]))
        for i in range(len(ordered)):
            for j in range(i + 1, len(ordered)):
                a, b = ordered[i], ordered[j]
                if int(b["start"]) >= int(a["end"]):
                    break
                if _overlaps(a, b):
                    conflicts.append({
                        "resource": resource, "tasks": [a["task"], b["task"]],
                        "overlap_start": max(int(a["start"]), int(b["start"])),
                        "overlap_end": min(int(a["end"]), int(b["end"])),
                    })
    return {"status": "ok", "has_conflicts": bool(conflicts),
            "n_conflicts": len(conflicts), "conflicts": conflicts}


def gantt_data(tasks: list, **kwargs: Any) -> dict[str, Any]:
    """Gantt-chart-ready records from ``{name, start, end[, resource]}``.

    Each task becomes ``{label, start, duration, resource}`` suitable for a
    plotting library; also returns the overall span.
    """
    if not tasks:
        raise ValueError("'tasks' must be a non-empty list")
    bars = []
    for t in tasks:
        start, end = int(t["start"]), int(t["end"])
        if end <= start:
            raise ValueError(f"task {t.get('name')!r}: end must be > start")
        bars.append({"label": t.get("name", "task"), "start": start,
                     "duration": end - start, "resource": t.get("resource", "")})
    bars.sort(key=lambda b: (b["start"], b["label"]))
    span_end = max(b["start"] + b["duration"] for b in bars)
    return {"status": "ok", "n_tasks": len(bars),
            "span": {"start": min(b["start"] for b in bars), "end": span_end},
            "bars": bars}


run = skill_run({"fte_estimate": fte_estimate,
                 "timeline_conflict": timeline_conflict,
                 "gantt_data": gantt_data})
register_skill("resource_planning", run)
