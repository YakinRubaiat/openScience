"""Study design documentation skill: design description, variables table, CONSORT text."""

from __future__ import annotations

from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run

_DESIGNS = {
    "between": "between-subjects (independent groups): each participant/unit is assigned to exactly one condition",
    "within": "within-subjects (repeated measures): each participant/unit experiences all conditions",
    "mixed": "mixed design: at least one between-subjects factor and one within-subjects factor",
}


def describe_design(
    design_type: str = "between",
    factors: dict[str, list[str]] | None = None,
    n_groups: int | None = None,
    randomization: str | None = None,
    blinding: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Describe a study design (between / within / mixed) with factors and safeguards."""
    design_type = design_type.lower()
    if design_type not in _DESIGNS:
        raise ValueError(f"Unknown design_type {design_type!r}. Use one of {sorted(_DESIGNS)}")
    factors = factors or {}
    scope = (
        "between-subjects"
        if design_type == "between"
        else ("within-subjects" if design_type == "within" else None)
    )
    factor_desc = [
        {
            "name": name,
            "levels": list(levels),
            "n_levels": len(levels),
            "scope": scope or "unspecified (mixed)",
        }
        for name, levels in factors.items()
    ]
    n_cells = 1
    for levels in factors.values():
        n_cells *= max(len(levels), 1)
    return result(
        design_type=design_type,
        description=_DESIGNS[design_type],
        factors=factor_desc,
        n_factorial_cells=n_cells if factors else (n_groups or 1),
        randomization=randomization or "not specified",
        blinding=blinding or "not specified",
    )


def variables_table(
    variables: list[dict[str, Any]] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Normalize a list of variable specs into a documentation table (markdown).

    Each variable: {name, type (independent/dependent/covariate), measurement,
    levels_or_range}.
    """
    variables = variables or []
    header = "| Name | Role | Measurement | Levels / Range |"
    sep = "|---|---|---|---|"
    rows = [
        "| {name} | {type} | {measurement} | {levels_or_range} |".format(
            name=v.get("name", ""),
            type=v.get("type", v.get("role", "")),
            measurement=v.get("measurement", ""),
            levels_or_range=v.get("levels_or_range", ""),
        )
        for v in variables
    ]
    markdown = "\n".join([header, sep, *rows])
    return result(variables=variables, n_variables=len(variables), markdown=markdown)


def consort_diagram_text(
    enrolled: int = 0,
    assessed: int | None = None,
    excluded: int = 0,
    allocated: dict[str, int] | None = None,
    lost_to_followup: dict[str, int] | None = None,
    analyzed: dict[str, int] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Generate a text CONSORT-style flow diagram from stage counts."""
    assessed = enrolled if assessed is None else assessed
    allocated = allocated or {}
    lost_to_followup = lost_to_followup or {}
    analyzed = analyzed or {}

    lines = [
        "CONSORT Flow Diagram (text)",
        "=" * 40,
        f"Enrolled: {enrolled}",
        f"Assessed for eligibility: {assessed}",
        f"Excluded: {excluded}",
        "-" * 40,
    ]
    for arm, n in allocated.items():
        lost = lost_to_followup.get(arm, 0)
        ana = analyzed.get(arm, n - lost)
        lines.append(f"Arm [{arm}]:")
        lines.append(f"  Allocated: {n}")
        lines.append(f"  Lost to follow-up: {lost}")
        lines.append(f"  Analyzed: {ana}")
    lines.append("-" * 40)
    total_alloc = sum(allocated.values()) if allocated else 0
    total_analyzed = (
        sum(analyzed.values())
        if analyzed
        else sum(allocated.get(a, 0) - lost_to_followup.get(a, 0) for a in allocated)
    )
    lines.append(f"Total allocated: {total_alloc}")
    lines.append(f"Total analyzed: {total_analyzed}")
    return result(
        diagram="\n".join(lines),
        enrolled=enrolled,
        assessed=assessed,
        excluded=excluded,
        allocated=allocated,
        lost_to_followup=lost_to_followup,
        analyzed={a: analyzed.get(a, allocated.get(a, 0) - lost_to_followup.get(a, 0)) for a in allocated},
        total_allocated=total_alloc,
        total_analyzed=total_analyzed,
    )


run = skill_run(
    {
        "describe_design": describe_design,
        "variables_table": variables_table,
        "consort_diagram_text": consort_diagram_text,
    }
)

register_skill("study_design_documentation", run)
