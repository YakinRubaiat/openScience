"""Future-work synthesis skill (deterministic templates).

Implements ``future_work_synthesis``:

- ``from_limitations``: turn each limitation sentence into a future-direction
  sentence of the form "Future work should address <limitation> ...".
- ``merge``: merge multiple lists of future-direction sentences, deduplicating
  case-insensitively while preserving first-seen order.
"""

from __future__ import annotations

import re
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap

_LEAD_RE = re.compile(
    r"^(our study (has|had)|this study (has|had)|the study (has|had)|"
    r"we (acknowledge|note|recogni[sz]e))\s+",
    re.IGNORECASE,
)


def _end_period(text: str) -> str:
    text = text.rstrip()
    if text and text[-1] not in ".!?":
        return text + "."
    return text


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(v) for v in value]


def _limitation_core(limitation: str) -> str:
    """Strip boilerplate lead-ins so the direction reads naturally."""
    core = _LEAD_RE.sub("", limitation.strip())
    core = re.sub(r"^(is|was|were|are|include[sd]?|remain[s]?)\s+", "", core,
                  flags=re.IGNORECASE)
    core = re.sub(r"^(a|an|the)\s+", "", core, flags=re.IGNORECASE)
    return core.rstrip(".").strip()


def from_limitations(limitations: Any = None, **_: Any) -> dict[str, Any]:
    """Convert each limitation into a future-direction sentence."""
    items = _as_list(limitations)
    directions: list[str] = []
    for lim in items:
        core = _limitation_core(lim)
        if not core:
            continue
        core = core[0].lower() + core[1:] if core else core
        directions.append(_end_period(
            f"Future work should address {core} to strengthen these findings"
        ))
    return result(future_directions=directions, count=len(directions))


def merge(lists: Any = None, **_: Any) -> dict[str, Any]:
    """Merge lists of future directions, deduplicating case-insensitively.

    ``lists`` accepts a list of lists, a single list of strings, or a string.
    """
    flat: list[str] = []
    if isinstance(lists, str):
        flat = [lists]
    else:
        for entry in lists or []:
            flat.extend(_as_list(entry))

    seen: set[str] = set()
    merged: list[str] = []
    for item in flat:
        key = re.sub(r"\s+", " ", item.strip().lower())
        if key and key not in seen:
            seen.add(key)
            merged.append(_end_period(item.strip()))
    return result(merged=merged, count=len(merged),
                  duplicates_removed=len(flat) - len(merged))


_OPERATIONS = {"from_limitations": from_limitations, "merge": merge}


def run(operation: str = "run", **kwargs: Any) -> Any:
    op = _OPERATIONS.get(operation) or _OPERATIONS["from_limitations"]
    if operation not in _OPERATIONS and operation != "run":
        raise ValueError(
            f"Unknown operation {operation!r}. Available: {sorted(_OPERATIONS)}"
        )
    return op(**unwrap(kwargs))


register_skill("future_work_synthesis", run)
