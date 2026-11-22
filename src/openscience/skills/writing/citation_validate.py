"""Citation validation skill (deterministic).

Implements ``citation_validation``:

- ``validate_entry``: check a single reference dict for required fields,
  sane publication year and a well-formed DOI; return a list of issue strings.
- ``report``: validate a list of entries and aggregate a summary report.
"""

from __future__ import annotations

import re
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap

_REQUIRED_FIELDS = ("authors", "title", "journal", "year")
_DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
_MIN_YEAR, _MAX_YEAR = 1600, 2100


def validate_entry(entry: Any = None, **_: Any) -> dict[str, Any]:
    """Validate one reference dict; return ``issues`` and ``valid``."""
    ref = entry if isinstance(entry, dict) else {}
    issues: list[str] = []

    for field in _REQUIRED_FIELDS:
        value = ref.get(field)
        if value is None or value == "" or value == []:
            issues.append(f"missing required field: {field}")

    year_val = ref.get("year")
    if year_val not in (None, ""):
        try:
            year = int(str(year_val)[:4])
            if not (_MIN_YEAR <= year <= _MAX_YEAR):
                issues.append(f"implausible year: {year_val}")
        except (TypeError, ValueError):
            issues.append(f"unparseable year: {year_val}")

    doi = ref.get("doi")
    if doi and not _DOI_RE.match(str(doi).strip()):
        issues.append(f"invalid doi format: {doi}")

    return result(valid=not issues, issues=issues, checked_fields=list(_REQUIRED_FIELDS))


def report(entries: Any = None, **_: Any) -> dict[str, Any]:
    """Validate a list of entries and aggregate a summary report."""
    refs = [e for e in (entries or []) if isinstance(e, dict)]
    per_entry = [validate_entry(e) for e in refs]
    invalid = [i for i, r in enumerate(per_entry) if not r["valid"]]
    return result(
        total=len(refs),
        valid=len(refs) - len(invalid),
        invalid=len(invalid),
        invalid_indices=invalid,
        entries=per_entry,
    )


_OPERATIONS = {"validate_entry": validate_entry, "report": report}


def run(operation: str = "run", **kwargs: Any) -> Any:
    op = _OPERATIONS.get(operation) or _OPERATIONS["validate_entry"]
    if operation not in _OPERATIONS and operation != "run":
        raise ValueError(
            f"Unknown operation {operation!r}. Available: {sorted(_OPERATIONS)}"
        )
    return op(**unwrap(kwargs))


register_skill("citation_validation", run)
