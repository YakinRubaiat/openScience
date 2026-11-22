"""timeline_estimation skill: CPM scheduling on task DAGs.

Critical Path Method over tasks with durations and dependencies:
earliest start/finish for every task, total slack, and the critical path.

Operations: ``critical_path``, ``earliest_schedule``, ``slack``.

Task spec: ``[{"name": "A", "duration": 3, "deps": ["B", "C"]}, ...]``
"""

from __future__ import annotations

from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run


def _topo(tasks: dict[str, dict[str, Any]]) -> list[str]:
    order, seen = [], set()

    def visit(name: str, stack: tuple[str, ...]) -> None:
        if name in stack:
            raise ValueError(f"cycle in dependencies: {' -> '.join(stack + (name,))}")
        if name in seen:
            return
        if name not in tasks:
            raise ValueError(f"unknown dependency {name!r}")
        for dep in tasks[name]["deps"]:
            visit(dep, stack + (name,))
        seen.add(name)
        order.append(name)

    for n in tasks:
        visit(n, ())
    return order


def _schedule(spec: list[dict[str, Any]]) -> dict[str, Any]:
    tasks: dict[str, dict[str, Any]] = {}
    for t in spec:
        name = t.get("name")
        if not name:
            raise ValueError("each task needs a 'name'")
        dur = float(t.get("duration", 0))
        if dur < 0:
            raise ValueError(f"task {name!r}: duration must be >= 0")
        tasks[name] = {"duration": dur, "deps": [str(d) for d in t.get("deps", [])]}
    order = _topo(tasks)
    es: dict[str, float] = {}
    ef: dict[str, float] = {}
    for n in order:
        es[n] = max((ef[d] for d in tasks[n]["deps"]), default=0.0)
        ef[n] = es[n] + tasks[n]["duration"]
    horizon = max(ef.values(), default=0.0)
    successors: dict[str, list[str]] = {n: [] for n in tasks}
    for n, t in tasks.items():
        for d in t["deps"]:
            successors[d].append(n)
    lf: dict[str, float] = {}
    ls: dict[str, float] = {}
    for n in reversed(order):
        lf[n] = min((ls[s] for s in successors[n]), default=horizon)
        ls[n] = lf[n] - tasks[n]["duration"]
    slacks = {n: ls[n] - es[n] for n in order}
    path = [n for n in order if abs(slacks[n]) < 1e-9]
    # order path nodes by earliest start for readability
    path.sort(key=lambda n: es[n])
    return {"tasks": tasks, "es": es, "ef": ef, "ls": ls, "lf": lf,
            "slack": slacks, "horizon": horizon, "critical_path": path}


def _check_spec(tasks: Any) -> list[dict[str, Any]]:
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("'tasks' must be a non-empty list")
    return tasks


def critical_path(tasks: list, **kwargs: Any) -> dict[str, Any]:
    """Critical path through the task DAG and the project duration."""
    sched = _schedule(_check_spec(tasks))
    return {"status": "ok", "duration": sched["horizon"],
            "critical_path": sched["critical_path"],
            "n_critical_tasks": len(sched["critical_path"])}


def earliest_schedule(tasks: list, **kwargs: Any) -> dict[str, Any]:
    """Earliest start/finish for every task, in dependency order."""
    sched = _schedule(_check_spec(tasks))
    schedule = [{"name": n, "earliest_start": sched["es"][n],
                 "earliest_finish": sched["ef"][n],
                 "duration": sched["tasks"][n]["duration"]}
                for n in sorted(sched["tasks"], key=lambda k: (sched["es"][k], k))]
    return {"status": "ok", "project_duration": sched["horizon"],
            "schedule": schedule}


def slack(tasks: list, **kwargs: Any) -> dict[str, Any]:
    """Total slack per task (0 == on the critical path)."""
    sched = _schedule(_check_spec(tasks))
    return {"status": "ok", "project_duration": sched["horizon"],
            "slack": sched["slack"],
            "free_critical_tasks": [n for n, s in sched["slack"].items() if s == 0]}


run = skill_run({"critical_path": critical_path,
                 "earliest_schedule": earliest_schedule, "slack": slack})
register_skill("timeline_estimation", run)
