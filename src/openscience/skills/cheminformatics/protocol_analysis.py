"""Protocol text-analysis skill.

Registers:
- ``protocol_analysis``

Parses numbered protocol text into structured steps and applies simple
duration / risk heuristics.
"""

from __future__ import annotations

import re
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run

_NUMBERED_STEP_RE = re.compile(r"^\s*(?:\(?\d+[\)\.:]|\d+\.\s|\d+\)\s)", re.IGNORECASE)
_DURATION_RE = re.compile(
    r"(?P<amount>\d+(?:\.\d+)?)\s*(?P<unit>hours?|hrs?|h\b|minutes?|mins?|m\b|seconds?|secs?|s\b)",
    re.IGNORECASE,
)

_RISK_KEYWORDS = [
    ("toxic", "toxic_reagent", "high"),
    ("carcinogen", "carcinogen", "high"),
    ("teratogen", "carcinogen", "high"),
    ("mutagen", "carcinogen", "high"),
    ("corrosive", "corrosive", "high"),
    ("biohazard", "biohazard", "high"),
    ("radioactive", "radioactive", "high"),
    ("autoclave", "heat_hazard", "medium"),
    ("centrifuge", "mechanical_hazard", "medium"),
    ("centrifug", "mechanical_hazard", "medium"),
    ("vortex", "mechanical_hazard", "low"),
    ("incubat", "time_sensitive", "low"),
    ("overnight", "time_sensitive", "medium"),
    ("on ice", "temperature_sensitive", "low"),
]

_UNIT = {
    "h": 60.0, "hr": 60.0, "hrs": 60.0, "hour": 60.0, "hours": 60.0,
    "m": 1.0, "min": 1.0, "mins": 1.0, "minute": 1.0, "minutes": 1.0,
    "s": 1.0 / 60.0, "sec": 1.0 / 60.0, "secs": 1.0 / 60.0, "second": 1.0 / 60.0, "seconds": 1.0 / 60.0,
}


def parse_steps(protocol_text: str, **kwargs: Any) -> dict[str, Any]:
    """Split numbered protocol text into indexed steps.

    Falls back to paragraph chunks when no numbered lines are found.
    """
    if not protocol_text or not protocol_text.strip():
        raise ValueError("Empty protocol_text")
    lines = protocol_text.splitlines()
    steps: list[str] = []
    current: list[str] = []
    for line in lines:
        if _NUMBERED_STEP_RE.match(line):
            if current:
                steps.append(" ".join(current).strip())
            current = [_NUMBERED_STEP_RE.sub("", line).strip()]
        elif line.strip() == "":
            if current:
                steps.append(" ".join(current).strip())
                current = []
        else:
            current.append(line.strip())
    if current:
        steps.append(" ".join(current).strip())
    if not steps:
        steps = [l.strip() for l in lines if l.strip()]
    return result(steps=steps, n_steps=len(steps))


def _duration_minutes(text: str) -> float | None:
    m = _DURATION_RE.search(text)
    if not m:
        return None
    amount = float(m.group("amount"))
    unit = m.group("unit").lower()
    return amount * _UNIT.get(unit, 0.0)


def estimate_duration(steps: list[str], **kwargs: Any) -> dict[str, Any]:
    """Heuristic per-step durations in minutes, summed to a total.

    Keyword heuristics:
    - explicit time strings ("30 min", "2 h") are parsed;
    - ``incubat`` adds 30 min by default when no explicit time is given;
    - ``wash`` / ``rinse`` adds 5 min per occurrence;
    - ``centrifug`` adds 10 min;
    - ``on ice for`` shortens long incubations by capping at 240 min.
    """
    if not steps:
        raise ValueError("steps must be a non-empty list")
    out_steps = []
    total = 0.0
    for idx, step in enumerate(steps):
        text = str(step)
        minutes = _duration_minutes(text)
        if minutes is None:
            low = text.lower()
            if "incubat" in low:
                minutes = 30.0
            elif "wash" in low or "rinse" in low:
                minutes = 5.0
            elif "centrifug" in low:
                minutes = 10.0
            elif "mix" in low or "vortex" in low:
                minutes = 1.0
            elif "overnight" in low:
                minutes = 60.0 * 14.0
        out_steps.append(
            {
                "step_index": idx,
                "text": text,
                "duration_minutes": minutes,
            }
        )
        total += minutes or 0.0
    return result(steps=out_steps, n_steps=len(out_steps), total_minutes=total)


def flag_risks(steps: list[str], **kwargs: Any) -> dict[str, Any]:
    """Attach hazard flags to each step based on a small keyword list."""
    if not steps:
        raise ValueError("steps must be a non-empty list")
    out_steps = []
    n_flagged = 0
    for idx, step in enumerate(steps):
        text = str(step)
        low = text.lower()
        tags = sorted({tag for kw, tag, _ in _RISK_KEYWORDS if kw in low})
        severity = "low"
        for kw, tag, sev in _RISK_KEYWORDS:
            if kw in low and (severity == "low" or sev == "high"):
                severity = sev
        out_steps.append(
            {
                "step_index": idx,
                "text": text,
                "risk_tags": tags,
                "severity": severity,
            }
        )
        if tags:
            n_flagged += 1
    return result(steps=out_steps, n_steps=len(out_steps), n_flagged=n_flagged)


run = skill_run(
    {
        "parse_steps": parse_steps,
        "estimate_duration": estimate_duration,
        "flag_risks": flag_risks,
    }
)

register_skill("protocol_analysis", run)
