"""Submission guidelines checking skill (deterministic).

Implements ``submission_guidelines``:

- ``word_limit_check``: compare a text's word count against a limit and
  report whether it complies and by how much.
- ``section_requirements``: verify a manuscript dict contains every required
  section plus any optional ones present.
- ``figure_count_check``: verify figure/table counts against maxima.
"""

from __future__ import annotations

import re
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w[\w'-]*\b", text))


def word_limit_check(text: str = "", word_limit: int = 5000, **_: Any) -> dict[str, Any]:
    """Compare ``text``'s word count against ``word_limit``."""
    count = _word_count(text)
    over = max(0, count - int(word_limit))
    return result(
        word_count=count,
        word_limit=int(word_limit),
        over_by=over,
        under_by=max(0, int(word_limit) - count),
        compliant=over == 0,
    )


def section_requirements(manuscript: Any = None, required: Any = None,
                         optional: Any = None, **_: Any) -> dict[str, Any]:
    """Check a manuscript dict contains required sections."""
    manuscript = manuscript if isinstance(manuscript, dict) else {}
    keys = {str(k).lower().replace(" ", "_") for k in manuscript if str(manuscript[k]).strip()}

    def _norm(items: Any) -> list[str]:
        if isinstance(items, str):
            items = [items]
        return [str(s).lower().replace(" ", "_") for s in (items or [])]

    req = _norm(required)
    opt = _norm(optional)
    missing = [s for s in req if s not in keys]
    present_optional = [s for s in opt if s in keys]
    return result(
        required=req,
        optional=opt,
        present=sorted(keys),
        missing=missing,
        present_optional=present_optional,
        compliant=not missing,
    )


def figure_count_check(manuscript: Any = None, max_figures: int | None = None,
                       max_tables: int | None = None, **_: Any) -> dict[str, Any]:
    """Count ``Figure n:``-style captions and ``Table n``-style captions.

    ``manuscript`` may be a raw text string or a dict of section -> text.
    """
    if isinstance(manuscript, dict):
        text = "\n\n".join(str(v) for v in manuscript.values())
    else:
        text = str(manuscript or "")

    figures = {int(n) for n in re.findall(r"\bFigure\s+(\d+)\s*[.:]", text)}
    tables = {int(n) for n in re.findall(r"\bTable\s+(\d+)\s*[.:]", text)}
    violations: list[str] = []
    if max_figures is not None and len(figures) > int(max_figures):
        violations.append(f"too many figures ({len(figures)} > {int(max_figures)})")
    if max_tables is not None and len(tables) > int(max_tables):
        violations.append(f"too many tables ({len(tables)} > {int(max_tables)})")
    return result(
        figure_count=len(figures),
        table_count=len(tables),
        figures=sorted(figures),
        tables=sorted(tables),
        violations=violations,
        compliant=not violations,
    )


_OPERATIONS = {
    "word_limit_check": word_limit_check,
    "section_requirements": section_requirements,
    "figure_count_check": figure_count_check,
}


def run(operation: str = "run", **kwargs: Any) -> Any:
    op = _OPERATIONS.get(operation) or _OPERATIONS["word_limit_check"]
    if operation not in _OPERATIONS and operation != "run":
        raise ValueError(
            f"Unknown operation {operation!r}. Available: {sorted(_OPERATIONS)}"
        )
    return op(**unwrap(kwargs))


register_skill("submission_guidelines", run)
