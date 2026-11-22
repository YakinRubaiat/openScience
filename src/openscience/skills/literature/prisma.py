"""prisma_workflow skill: PRISMA flow counts, validation and text diagram."""

from __future__ import annotations

from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap

_STAGES = ("identified", "deduplicated", "screened", "fulltext", "included")


def flow_counts(**kwargs: Any) -> dict[str, Any]:
    """Compute per-stage exclusion counts from the given stage counts (pure).

    Accepts kwargs like ``identified=1000, screened=200, included=25``.
    """
    kw = unwrap(kwargs)
    counts = {s: int(kw.get(s, 0) or 0) for s in _STAGES if kw.get(s) is not None}
    stages = list(counts)
    exclusions = {}
    for a, b in zip(stages, stages[1:]):
        exclusions[f"{a}_to_{b}_excluded"] = counts[a] - counts[b]
    return result(counts=counts, exclusions=exclusions)


def validate(**kwargs: Any) -> dict[str, Any]:
    """Consistency check: identified >= ... >= included, and no negatives.

    Raises ValueError when the funnel is inconsistent.
    """
    kw = unwrap(kwargs)
    counts = {s: int(kw.get(s, 0) or 0) for s in _STAGES if kw.get(s) is not None}
    errors = []
    prev_name, prev_val = None, None
    for s in _STAGES:
        if s not in counts:
            continue
        v = counts[s]
        if v < 0:
            errors.append(f"{s} is negative ({v})")
        if prev_val is not None and v > prev_val:
            errors.append(f"{s} ({v}) > {prev_name} ({prev_val})")
        prev_name, prev_val = s, v
    if errors:
        return result(valid=False, errors=errors)
    return result(valid=True, errors=[])


def diagram_text(**kwargs: Any) -> dict[str, Any]:
    """ASCII PRISMA flow diagram from stage counts (pure)."""
    kw = unwrap(kwargs)
    counts = {s: int(kw.get(s, 0) or 0) for s in _STAGES if kw.get(s) is not None}
    lines = ["PRISMA Flow Diagram", "==================="]
    prev = None
    for s in _STAGES:
        if s not in counts:
            continue
        lines.append(f"| {s}: n = {counts[s]}")
        if prev is not None:
            lines.insert(len(lines) - 1, f"|   (excluded: {counts[prev] - counts[s]})")
        prev = s
    return result(diagram="\n".join(lines))


_OPS = {"flow_counts": flow_counts, "validate": validate, "diagram_text": diagram_text}


def run(operation: str = "run", **kwargs: Any) -> dict[str, Any]:
    """Dispatch to an operation; ``run`` defaults to ``flow_counts``."""
    op = _OPS.get(operation) or _OPS["flow_counts"]
    if operation not in _OPS and operation != "run":
        raise ValueError(f"Unknown operation {operation!r}. Available: {sorted(_OPS)}")
    return op(**kwargs)


register_skill("prisma_workflow", run)
