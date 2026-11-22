"""workflow_tracking skill: step-level workflow execution history."""

from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run

# In-memory history: ordered list of step events.
_HISTORY: list[dict[str, Any]] = []


def track_step(step: str, status: str = "ok",
               inputs: list[str] | None = None,
               outputs: list[str] | None = None,
               duration_s: float | None = None,
               metadata: dict[str, Any] | None = None,
               log_file: str | None = None) -> dict[str, Any]:
    """Record a workflow step event (in-memory, optional jsonl append)."""
    if status not in ("ok", "started", "failed", "skipped"):
        raise ValueError(f"Unknown status {status!r}")
    event = {
        "seq": len(_HISTORY),
        "step": step,
        "status": status,
        "inputs": list(inputs or []),
        "outputs": list(outputs or []),
        "duration_s": duration_s,
        "metadata": dict(metadata or {}),
        "timestamp": time.time(),
    }
    _HISTORY.append(event)
    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as fh:
            fh.write(json.dumps(event) + "\n")
    return result(**event)


def get_history(log_file: str | None = None,
                last_n: int | None = None) -> dict[str, Any]:
    """Return recorded step events, newest last.

    ``log_file`` reads from a jsonl file instead of the in-memory store.
    """
    if log_file:
        path = Path(log_file)
        if not path.exists():
            raise FileNotFoundError(f"Log file not found: {path}")
        events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    else:
        events = list(_HISTORY)
    if last_n is not None:
        events = events[-int(last_n):]
    return result(n_events=len(events), events=events)


def summarize(log_file: str | None = None) -> dict[str, Any]:
    """Aggregate step statuses, durations and IO coverage."""
    events = get_history(log_file)["events"]
    statuses = Counter(e["status"] for e in events)
    durations = [e["duration_s"] for e in events if e.get("duration_s") is not None]
    steps = Counter(e["step"] for e in events)
    return result(
        n_events=len(events),
        n_unique_steps=len(steps),
        status_counts=dict(statuses),
        step_counts=dict(steps),
        total_duration_s=float(sum(durations)) if durations else 0.0,
        all_ok=statuses.get("failed", 0) == 0,
    )


def clear() -> dict[str, Any]:
    """Reset the in-memory history."""
    n = len(_HISTORY)
    _HISTORY.clear()
    return result(cleared=n)


_OPS = {
    "track_step": track_step,
    "get_history": get_history,
    "summarize": summarize,
    "clear": clear,
}

run = skill_run(_OPS)
register_skill("workflow_tracking", run)
