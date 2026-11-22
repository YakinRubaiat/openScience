"""Preregistration templates skill: markdown rendering, AsPredicted format, checklist."""

from __future__ import annotations

import datetime as _dt
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run

_CHECKLIST_ITEMS: list[tuple[str, str]] = [
    ("title", "Study title stated"),
    ("hypotheses", "Specific, falsifiable hypotheses listed"),
    ("design", "Experimental design described (conditions, factors)"),
    ("sample_size", "Sample size justified (power analysis or stopping rule)"),
    ("randomization", "Randomization procedure specified"),
    ("blinding", "Blinding / masking procedure specified"),
    ("primary_outcome", "Primary outcome variable defined"),
    ("exclusion_criteria", "Data exclusion criteria defined a priori"),
    ("analysis_plan", "Statistical tests and models specified"),
    ("multiple_comparisons", "Correction for multiple comparisons stated"),
    ("missing_data", "Missing-data handling plan stated"),
]


def render(
    title: str = "",
    authors: list[str] | None = None,
    hypotheses: list[str] | str | None = None,
    design: str | dict[str, Any] = "",
    analysis_plan: str | list[str] = "",
    date: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Render a preregistration document as markdown."""
    date = date or _dt.date.today().isoformat()
    if isinstance(hypotheses, str):
        hypotheses = [hypotheses] if hypotheses else []
    hypotheses = hypotheses or []
    if isinstance(analysis_plan, list):
        analysis_plan_md = "\n".join(f"- {s}" for s in analysis_plan)
    else:
        analysis_plan_md = analysis_plan or "(to be filled in)"
    if isinstance(design, dict):
        design_md = "\n".join(f"- **{k}**: {v}" for k, v in design.items())
    else:
        design_md = design or "(to be filled in)"
    authors_md = ", ".join(authors) if authors else "(authors)"

    md = f"""# Preregistration: {title or '(title)'}

**Authors:** {authors_md}
**Date:** {date}

## Hypotheses

{chr(10).join(f"{i + 1}. {h}" for i, h in enumerate(hypotheses)) or '(to be filled in)'}

## Study Design

{design_md}

## Analysis Plan

{analysis_plan_md}
"""
    return result(format="markdown", markdown=md, title=title, date=date)


def aspredicted_format(
    title: str = "",
    data_collection: str = "",
    hypothesis: str = "",
    dependent_variable: str = "",
    conditions: str = "",
    analyses: str = "",
    outliers_exclusions: str = "",
    sample_size: str = "",
    other: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    """Render the standard 8-question AsPredicted format as markdown."""
    fields = [
        ("Have any data been collected for this study already?", data_collection),
        ("What's the main question being asked or hypothesis being tested?", hypothesis),
        ("Describe the key dependent variable(s).", dependent_variable),
        ("How many and which conditions will participants be assigned to?", conditions),
        ("Specify exactly which analyses you will conduct.", analyses),
        ("Describe exactly how outliers will be defined and handled.", outliers_exclusions),
        ("How many observations will be collected?", sample_size),
        ("Anything else you would like to pre-register?", other),
    ]
    lines = [f"# AsPredicted Preregistration: {title or '(title)'}", ""]
    for i, (q, a) in enumerate(fields, start=1):
        lines.append(f"## {i}. {q}")
        lines.append("")
        lines.append(a or "(to be filled in)")
        lines.append("")
    return result(format="aspredicted", markdown="\n".join(lines), title=title)


def checklist(
    completed: list[str] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Return a preregistration completeness checklist.

    Pass ``completed=[item_keys]`` to mark items done; returns remaining gaps.
    """
    completed = completed or []
    items = [
        {"key": k, "description": d, "completed": k in completed}
        for k, d in _CHECKLIST_ITEMS
    ]
    missing = [i["key"] for i in items if not i["completed"]]
    return result(
        items=items,
        n_items=len(items),
        n_completed=len(items) - len(missing),
        missing=missing,
        complete=not missing,
    )


run = skill_run(
    {
        "render": render,
        "aspredicted_format": aspredicted_format,
        "checklist": checklist,
    }
)

register_skill("preregistration_templates", run)
