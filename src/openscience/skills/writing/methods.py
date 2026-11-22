"""Methodology (IMRaD Methods) writing skill (deterministic templates).

Implements ``methodology_writing``:

- ``render``: structured sections {materials, steps, analysis} -> past-tense
  Methods prose in IMRaD style.
- ``checklist``: checks a methods text for expected components (design,
  materials, procedures, analysis/statistics, reproducibility cues) and
  returns the missing ones.
"""

from __future__ import annotations

import re
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap


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


def render(materials: Any = None, steps: Any = None, analysis: Any = None,
           design: str = "", **_: Any) -> dict[str, Any]:
    """Render structured {materials, steps, analysis} into IMRaD methods prose.

    ``materials``/``steps``/``analysis`` accept a string or a list of strings.
    Steps are rendered as a past-tense narrative in given order.
    """
    sections: list[str] = []
    headings: list[str] = []

    if design:
        sections.append(_end_period(f"Study design. {design}"))
        headings.append("study_design")

    mats = _as_list(materials)
    if mats:
        body = " ".join(_end_period(m) for m in mats)
        sections.append(_end_period(f"Materials. {body}"))
        headings.append("materials")

    step_list = _as_list(steps)
    if step_list:
        body = " ".join(_end_period(s) for s in step_list)
        sections.append(_end_period(f"Procedures. {body}"))
        headings.append("procedures")

    analyses = _as_list(analysis)
    if analyses:
        body = " ".join(_end_period(a) for a in analyses)
        sections.append(_end_period(f"Data analysis. {body}"))
        headings.append("analysis")

    if not sections:
        sections.append("Methods were not provided in structured form.")

    methods_text = "\n\n".join(sections)
    return result(
        methods=methods_text,
        sections=headings,
        word_count=len(re.findall(r"\b\w[\w'-]*\b", methods_text)),
    )


_CHECKLIST_PATTERNS: list[tuple[str, str]] = [
    ("study_design", r"\b(design|cohort|trial|cross-sectional|randomi[sz]ed)\b"),
    ("materials", r"\b(material|reagent|sample|specimen|instrument|kit)s?\b"),
    ("procedures", r"\b(procedure|protocol|step|incubat\w*|centrifug\w*|pipett\w*|inject\w*)\b"),
    ("analysis", r"\b(analy[sz]is|statistic\w*|regression|test|model)s?\b"),
    ("reproducibility", r"\b(replicat\w*|repeat\w*|blind\w*|control\w*|calibrat\w*)\b"),
]


def checklist(text: str = "", **_: Any) -> dict[str, Any]:
    """Check a methods text for expected components; return present/missing."""
    text_l = text.lower()
    present = [name for name, pat in _CHECKLIST_PATTERNS if re.search(pat, text_l)]
    missing = [name for name, _ in _CHECKLIST_PATTERNS if name not in present]
    return result(
        present=present,
        missing=missing,
        complete=not missing,
        checked=[name for name, _ in _CHECKLIST_PATTERNS],
    )


_OPERATIONS = {"render": render, "checklist": checklist}


def run(operation: str = "run", **kwargs: Any) -> Any:
    op = _OPERATIONS.get(operation) or _OPERATIONS["render"]
    if operation not in _OPERATIONS and operation != "run":
        raise ValueError(
            f"Unknown operation {operation!r}. Available: {sorted(_OPERATIONS)}"
        )
    return op(**unwrap(kwargs))


register_skill("methodology_writing", run)
