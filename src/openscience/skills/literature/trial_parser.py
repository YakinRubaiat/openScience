"""trial_parser skill: flatten nested CT.gov study dicts to tables (pure)."""

from __future__ import annotations

from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap


def parse(**kwargs: Any) -> dict[str, Any]:
    """Flatten a nested CT.gov v2 study dict into a flat record (pure)."""
    kw = unwrap(kwargs)
    study = kw.get("study") or kw.get("json") or {}
    proto = study.get("protocolSection") or {}
    ident = proto.get("identificationModule") or {}
    status = proto.get("statusModule") or {}
    design = proto.get("designModule") or {}
    flat = {
        "nct_id": ident.get("nctId") or "",
        "title": ident.get("briefTitle") or "",
        "org": (ident.get("organization") or {}).get("fullName") or "",
        "status": status.get("overallStatus") or "",
        "start_date": (status.get("startDateStruct") or {}).get("date") or "",
        "completion_date": (status.get("completionDateStruct") or {}).get("date") or "",
        "phases": ", ".join(design.get("phases") or []),
        "enrollment": (design.get("enrollmentInfo") or {}).get("count"),
        "study_type": design.get("studyType") or "",
    }
    return result(flat=flat)


def arms_table(**kwargs: Any) -> dict[str, Any]:
    """Extract arm/intervention rows from a CT.gov study dict (pure)."""
    study = unwrap(kwargs).get("study") or {}
    proto = (study.get("protocolSection") or {})
    arms = proto.get("armsInterventionsModule") or {}
    rows = []
    for arm in arms.get("armGroups") or []:
        rows.append(
            {
                "label": arm.get("label") or "",
                "type": arm.get("type") or "",
                "description": (arm.get("description") or "")[:200],
            }
        )
    for iv in arms.get("interventions") or []:
        rows.append(
            {
                "label": iv.get("name") or "",
                "type": iv.get("type") or "",
                "description": (iv.get("description") or "")[:200],
            }
        )
    return result(rows=rows, count=len(rows))


def eligibility_extract(**kwargs: Any) -> dict[str, Any]:
    """Extract eligibility criteria fields from a CT.gov study dict (pure)."""
    study = unwrap(kwargs).get("study") or {}
    elig = (study.get("protocolSection") or {}).get("eligibilityModule") or {}
    return result(
        criteria=elig.get("eligibilityCriteria") or "",
        sex=elig.get("sex") or "",
        min_age=elig.get("minimumAge") or "",
        max_age=elig.get("maximumAge") or "",
        healthy_volunteers=elig.get("healthyVolunteers"),
    )


_OPS = {
    "parse": parse,
    "arms_table": arms_table,
    "eligibility_extract": eligibility_extract,
}


def run(operation: str = "run", **kwargs: Any) -> dict[str, Any]:
    """Dispatch to an operation; ``run`` defaults to ``parse``."""
    op = _OPS.get(operation) or _OPS["parse"]
    if operation not in _OPS and operation != "run":
        raise ValueError(f"Unknown operation {operation!r}. Available: {sorted(_OPS)}")
    return op(**kwargs)


register_skill("trial_parser", run)
