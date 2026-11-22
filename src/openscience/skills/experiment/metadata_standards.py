"""Metadata standards skill: MINSEQE/MIAME-lite validation, field suggestions, templates."""

from __future__ import annotations

from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run

# MINSEQE/MIAME-lite required fields: minimal information about a high-throughput
# sequencing / microarray experiment.
_REQUIRED_FIELDS: dict[str, str] = {
    "title": "Short descriptive title of the experiment",
    "summary": "Overall goal and summary of the experiment",
    "experiment_design": "Description of the experimental design",
    "contributor": "Name(s) of the investigator(s)",
    "organization": "Affiliation / organization",
    "organism": "Scientific name of the organism studied",
    "sample_source": "Source of the samples (tissue, cell line, etc.)",
    "sample_characteristics": "Key sample characteristics (age, sex, treatment, ...)",
    "molecule": "Extracted molecule type (total RNA, genomic DNA, ...)",
    "extraction_protocol": "Nucleic acid extraction protocol",
    "library_strategy": "Library strategy (RNA-Seq, ChIP-Seq, ...)",
    "library_construction_protocol": "Library construction protocol",
    "instrument_model": "Sequencing instrument model",
    "data_processing": "Description of data processing steps",
}

_OPTIONAL_FIELDS: dict[str, str] = {
    "keywords": "Free-text keywords",
    "pubmed_id": "PubMed identifier of a related publication",
    "geo_accession": "GEO series accession if deposited",
    "growth_protocol": "Growth / treatment protocol of the organism",
    "label_protocol": "Label protocol (arrays)",
    "hybridization_protocol": "Hybridization protocol (arrays)",
    "scan_protocol": "Scan protocol (arrays)",
    "normalization": "Normalization procedure applied",
    "quality_control": "QC measures applied",
    "contact_email": "Contact email address",
}


def validate_mininfo(
    metadata: dict[str, Any],
    profile: str = "MINSEQE",
    **kwargs: Any,
) -> dict[str, Any]:
    """Check required fields for a MINSEQE/MIAME-lite profile.

    Returns missing, empty, and present fields plus overall validity.
    """
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be a dict of field name -> value")

    missing: list[str] = []
    empty: list[str] = []
    present: list[str] = []
    for field in _REQUIRED_FIELDS:
        if field not in metadata:
            missing.append(field)
        elif metadata[field] is None or str(metadata[field]).strip() == "":
            empty.append(field)
        else:
            present.append(field)

    unknown = sorted(k for k in metadata if k not in _REQUIRED_FIELDS and k not in _OPTIONAL_FIELDS)
    return result(
        profile=profile.upper(),
        valid=not missing and not empty,
        missing_fields=missing,
        empty_fields=empty,
        present_fields=present,
        unknown_fields=unknown,
        n_required=len(_REQUIRED_FIELDS),
    )


def suggest_fields(
    metadata: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Suggest required/optional fields not yet populated in ``metadata``."""
    metadata = metadata or {}
    suggested_required = [
        {"field": f, "description": d}
        for f, d in _REQUIRED_FIELDS.items()
        if f not in metadata or not str(metadata.get(f, "")).strip()
    ]
    suggested_optional = [
        {"field": f, "description": d}
        for f, d in _OPTIONAL_FIELDS.items()
        if f not in metadata
    ]
    return result(
        suggested_required=suggested_required,
        suggested_optional=suggested_optional,
    )


def template(
    profile: str = "MINSEQE",
    include_optional: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    """Return a metadata template dict for the requested profile."""
    fields: dict[str, str] = {f: "" for f in _REQUIRED_FIELDS}
    if include_optional:
        fields.update({f: "" for f in _OPTIONAL_FIELDS})
    return result(
        profile=profile.upper(),
        template=fields,
        field_descriptions={**_REQUIRED_FIELDS, **({} if not include_optional else _OPTIONAL_FIELDS)},
        required=sorted(_REQUIRED_FIELDS),
    )


run = skill_run(
    {
        "validate_mininfo": validate_mininfo,
        "suggest_fields": suggest_fields,
        "template": template,
    }
)

register_skill("metadata_standards", run)
