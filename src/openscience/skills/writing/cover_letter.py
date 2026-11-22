"""Cover letter and rebuttal opening writing skill (deterministic templates).

Implements ``letter_writing``:

- ``render_cover_letter``: title + journal + findings + why -> a submission
  cover letter addressed to the editor.
- ``render_rebuttal_opening``: manuscript id + editor/reviewer thanks ->
  the opening paragraph of a point-by-point response letter.
"""

from __future__ import annotations

from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(v) for v in value]


def _end_period(text: str) -> str:
    text = text.rstrip()
    if text and text[-1] not in ".!?":
        return text + "."
    return text


_COVER_TEMPLATE = """\
Dear Dr. {editor},

We are pleased to submit our manuscript entitled "{title}" for consideration \
for publication in {journal}.

{findings_paragraph}

{why_paragraph}

This manuscript is original, has not been published previously, and is not \
under consideration by any other journal. All authors have approved the \
submission and declare no competing interests.

Sincerely,
{authors}
"""


def render_cover_letter(title: str = "", journal: str = "", findings: Any = None,
                        why: str = "", authors: str = "The Authors",
                        editor: str = "Editor", **_: Any) -> dict[str, Any]:
    """Compose a submission cover letter."""
    finding_items = _as_list(findings)
    if finding_items:
        joined = " ".join(_end_period(f) for f in finding_items)
        findings_paragraph = _end_period(
            f"In this study, {joined[0].lower() + joined[1:] if joined else joined}"
        )
    else:
        findings_paragraph = "In this study, we present new findings of broad interest."
    why_paragraph = _end_period(why) if why else (
        f"We believe this work is a strong fit for {journal or 'your journal'} "
        "and will be of interest to its readership."
    )
    letter = _COVER_TEMPLATE.format(
        editor=editor or "Editor",
        title=title or "Untitled",
        journal=journal or "your journal",
        findings_paragraph=findings_paragraph,
        why_paragraph=why_paragraph,
        authors=authors,
    ).strip()
    return result(letter=letter, journal=journal or "", title=title or "")


_REBUTTAL_TEMPLATE = """\
Dear Dr. {editor},

Thank you for your letter regarding our manuscript {manuscript_id} and for \
the opportunity to revise it. We are grateful to you{reviewer_phrase} for the \
constructive comments, which have substantially improved the paper. We have \
revised the manuscript accordingly; our point-by-point responses to each \
comment follow below. Changes in the revised manuscript are highlighted.

Sincerely,
{authors}
"""


def render_rebuttal_opening(manuscript_id: str = "", editor: str = "Editor",
                            reviewers: Any = None, authors: str = "The Authors",
                            **_: Any) -> dict[str, Any]:
    """Compose the opening paragraph of a point-by-point rebuttal letter."""
    reviewer_items = _as_list(reviewers)
    reviewer_phrase = (
        " and to the reviewers" if not reviewer_items
        else " and to " + ", ".join(reviewer_items)
    )
    letter = _REBUTTAL_TEMPLATE.format(
        editor=editor or "Editor",
        manuscript_id=manuscript_id or "(manuscript ID)",
        reviewer_phrase=reviewer_phrase,
        authors=authors,
    ).strip()
    return result(letter=letter, manuscript_id=manuscript_id or "")


_OPERATIONS = {
    "render_cover_letter": render_cover_letter,
    "render_rebuttal_opening": render_rebuttal_opening,
}


def run(operation: str = "run", **kwargs: Any) -> Any:
    op = _OPERATIONS.get(operation) or _OPERATIONS["render_cover_letter"]
    if operation not in _OPERATIONS and operation != "run":
        raise ValueError(
            f"Unknown operation {operation!r}. Available: {sorted(_OPERATIONS)}"
        )
    return op(**unwrap(kwargs))


register_skill("letter_writing", run)
