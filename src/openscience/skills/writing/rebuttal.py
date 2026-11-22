"""Reviewer response (rebuttal) writing skill (deterministic templates).

Implements ``response_writing``:

- ``point_by_point``: turn a list of reviewer comments into response items,
  each with a ``response`` and a ``change``+``justification`` sentence.
- ``summary_letter``: compose a short summary letter describing the overall
  changes made in the revision.
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


def point_by_point(comments: Any = None, **_: Any) -> dict[str, Any]:
    """Convert reviewer comments into response items with change + justification.

    ``comments`` is a list of strings or dicts with keys ``comment`` and
    optionally ``change`` / ``justification``.
    """
    items: list[dict[str, str]] = []
    raw = comments if isinstance(comments, list) else _as_list(comments)
    for i, c in enumerate(raw, start=1):
        if isinstance(c, dict):
            comment = str(c.get("comment", ""))
            change = str(c.get("change", ""))
            justification = str(c.get("justification", ""))
        else:
            comment, change, justification = str(c), "", ""
        if not change:
            change = "We have revised the manuscript to address this point"
        if not justification:
            justification = (
                "This change clarifies the manuscript and directly addresses "
                "the reviewer's concern"
            )
        items.append({
            "number": i,
            "comment": comment,
            "response": _end_period(
                f"Response: We thank the reviewer for this comment. {change}"
            ),
            "change": _end_period(change),
            "justification": _end_period(justification),
        })
    return result(items=items, count=len(items))


_SUMMARY_TEMPLATE = """\
Dear Dr. {editor},

We thank the editor and reviewers for their careful evaluation of our \
manuscript{manuscript_id}. In the revised version, we have made the \
following changes: {changes_summary} These revisions address all comments \
raised during review, and we believe the manuscript is substantially \
improved as a result.

Sincerely,
{authors}
"""


def summary_letter(changes: Any = None, manuscript_id: str = "",
                   editor: str = "Editor", authors: str = "The Authors",
                   **_: Any) -> dict[str, Any]:
    """Compose a summary-of-changes letter for a revised manuscript."""
    change_items = [_end_period(c) for c in _as_list(changes)]
    if change_items:
        joined = "; ".join(c.rstrip(".") for c in change_items) + "."
    else:
        joined = "minor editorial revisions."
    letter = _SUMMARY_TEMPLATE.format(
        editor=editor or "Editor",
        manuscript_id=f" ({manuscript_id})" if manuscript_id else "",
        changes_summary=joined + " ",
        authors=authors,
    ).strip()
    return result(letter=letter, changes=change_items, count=len(change_items))


_OPERATIONS = {
    "point_by_point": point_by_point,
    "summary_letter": summary_letter,
}


def run(operation: str = "run", **kwargs: Any) -> Any:
    op = _OPERATIONS.get(operation) or _OPERATIONS["point_by_point"]
    if operation not in _OPERATIONS and operation != "run":
        raise ValueError(
            f"Unknown operation {operation!r}. Available: {sorted(_OPERATIONS)}"
        )
    return op(**unwrap(kwargs))


register_skill("response_writing", run)
