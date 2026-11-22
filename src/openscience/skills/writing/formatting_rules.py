"""Manuscript formatting rules checker (deterministic, pure ``re``).

Implements ``formatting_rules``:

- ``check_heading_case``: verify headings use Title Case (first word and all
  major words capitalized); return violations with a suggested fix.
- ``check_figure_refs``: verify every ``Figure n`` reference has a matching
  figure caption ``Figure n.`` / ``Figure n:`` in the text.
- ``check_abbrev_defined``: verify each all-caps abbreviation is defined at
  least once as ``Full Name (ABBR)`` before/where it is used.
"""

from __future__ import annotations

import re
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap

_MINOR_WORDS = frozenset(
    "a an and as at but by for in nor of on or per the to vs via with from".split()
)
_FIG_REF_RE = re.compile(r"\bFigure\s+(\d+)\b")
_FIG_CAPTION_RE = re.compile(r"\bFigure\s+(\d+)\s*[.:]")
_ABBR_RE = re.compile(r"\b([A-Z]{2,6})\b")
_ABBR_DEF_RE = re.compile(r"\(([A-Z]{2,6})\)")

_ALL_HEADINGS_CAP = frozenset(
    "A AN AND AS AT BUT BY FOR IN NOR OF ON OR PER THE TO VS VIA WITH FROM"
    .split()
)


def _is_title_case(heading: str) -> bool:
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", heading)
    if not words:
        return True
    for i, word in enumerate(words):
        if word.isupper() and len(word) >= 2:  # acronym, fine
            continue
        if i > 0 and word.lower() in _MINOR_WORDS:
            continue
        if not word[0].isupper():
            return False
    return True


def check_heading_case(headings: Any = None, **_: Any) -> dict[str, Any]:
    """Check a list of headings for Title Case; return violations + fixes."""
    items = [str(h) for h in (headings or [])] if not isinstance(headings, str) else [headings]
    violations: list[dict[str, str]] = []
    for h in items:
        if not _is_title_case(h):
            fixed_words = []
            for i, word in enumerate(re.findall(r"[A-Za-z][A-Za-z'-]*", h)):
                if word.isupper() and len(word) >= 2:
                    fixed_words.append(word)
                elif i > 0 and word.lower() in _MINOR_WORDS:
                    fixed_words.append(word.lower())
                else:
                    fixed_words.append(word.capitalize())
            violations.append({"heading": h, "suggestion": " ".join(fixed_words)})
    return result(
        checked=len(items),
        valid=len(items) - len(violations),
        violations=violations,
        compliant=not violations,
    )


def check_figure_refs(text: str = "", **_: Any) -> dict[str, Any]:
    """Check every ``Figure n`` reference has a matching caption in ``text``."""
    refs = {int(n) for n in _FIG_REF_RE.findall(text)}
    captions = {int(n) for n in _FIG_CAPTION_RE.findall(text)}
    # a caption also counts as a reference to itself
    pure_refs = refs - captions
    missing = sorted(pure_refs - captions)
    unused_captions = sorted(captions - pure_refs)
    return result(
        references=sorted(refs),
        captions=sorted(captions),
        missing_captions=missing,
        uncited_figures=unused_captions,
        compliant=not missing,
    )


def check_abbrev_defined(text: str = "", **_: Any) -> dict[str, Any]:
    """Check each all-caps abbreviation is defined as ``Full Name (ABBR)``."""
    used = _ABBR_RE.findall(text)
    defined = set(_ABBR_DEF_RE.findall(text))
    # Count definitions themselves as usage of that abbreviation.
    undefined = sorted({a for a in used if a not in defined
                        and a.upper() not in _ALL_HEADINGS_CAP})
    return result(
        abbreviations=sorted(set(used)),
        defined=sorted(defined),
        undefined=undefined,
        compliant=not undefined,
    )


_OPERATIONS = {
    "check_heading_case": check_heading_case,
    "check_figure_refs": check_figure_refs,
    "check_abbrev_defined": check_abbrev_defined,
}


def run(operation: str = "run", **kwargs: Any) -> Any:
    op = _OPERATIONS.get(operation) or _OPERATIONS["check_heading_case"]
    if operation not in _OPERATIONS and operation != "run":
        raise ValueError(
            f"Unknown operation {operation!r}. Available: {sorted(_OPERATIONS)}"
        )
    return op(**unwrap(kwargs))


register_skill("formatting_rules", run)
