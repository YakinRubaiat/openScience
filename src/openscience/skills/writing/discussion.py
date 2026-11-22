"""Discussion writing skill (deterministic templates).

Implements ``discussion_writing``:

- ``render``: findings + prior_work + limitations + implications -> Discussion
  prose in the conventional order (principal finding, interpretation,
  comparison with prior work, limitations, implications, conclusion).
- ``paragraph_order_check``: verify that a discussion draft's paragraphs
  follow the expected rhetorical order.
- ``write_discussion``/``run``: backward-compatible alias of the renderer
  that also accepts the legacy parameter names used by scientific_writing.
"""

from __future__ import annotations

import re
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap

_EXPECTED_ORDER = ["findings", "prior_work", "limitations", "implications"]


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


def render(findings: Any = None, prior_work: Any = None, limitations: Any = None,
           implications: Any = None, conclusion: str = "", **_: Any) -> dict[str, Any]:
    """Compose a Discussion from findings / prior work / limitations / implications."""
    paragraphs: list[str] = []
    sections: list[str] = []

    finding_items = _as_list(findings)
    if finding_items:
        first = _end_period(f"In this study, {finding_items[0]}")
        rest = " ".join(_end_period(f) for f in finding_items[1:])
        paragraphs.append(f"{first} {rest}".strip())
        sections.append("findings")

    prior_items = _as_list(prior_work)
    if prior_items:
        body = " ".join(_end_period(p) for p in prior_items)
        paragraphs.append(_end_period(f"These findings are consistent with and extend prior work. {body}"))
        sections.append("prior_work")

    lim_items = _as_list(limitations)
    if lim_items:
        body = " ".join(_end_period(l) for l in lim_items)
        paragraphs.append(_end_period(f"Our study has limitations. {body}"))
        sections.append("limitations")

    imp_items = _as_list(implications)
    if imp_items:
        body = " ".join(_end_period(i) for i in imp_items)
        paragraphs.append(_end_period(f"These results have several implications. {body}"))
        sections.append("implications")

    if conclusion:
        paragraphs.append(_end_period(f"In conclusion, {conclusion}"))
        sections.append("conclusion")

    discussion = "\n\n".join(paragraphs).strip()
    return result(discussion=discussion, sections=sections,
                  word_count=len(re.findall(r"\b\w[\w'-]*\b", discussion)))


_PARAGRAPH_PATTERNS: list[tuple[str, str]] = [
    ("findings", r"\b(in this study|we (show|found|observed|demonstrated)|principal finding)\b"),
    ("prior_work", r"\b(prior|previous|consistent with|in contrast|literature|extend)\b"),
    ("limitations", r"\b(limitation|caveat|shortcoming|weakness)\b"),
    ("implications", r"\b(implication|future|translation|clinical|policy|further research)\b"),
]


def paragraph_order_check(discussion: str = "", **_: Any) -> dict[str, Any]:
    """Verify that discussion paragraphs follow the expected rhetorical order."""
    paragraphs = [p for p in re.split(r"\n\s*\n", discussion.strip()) if p.strip()]
    labels: list[str] = []
    for para in paragraphs:
        label = "other"
        for name, pattern in _PARAGRAPH_PATTERNS:
            if re.search(pattern, para, re.IGNORECASE):
                label = name
                break
        labels.append(label)

    expected = [l for l in labels if l in _EXPECTED_ORDER]
    order_positions = [(_EXPECTED_ORDER.index(l), i) for i, l in enumerate(labels)
                       if l in _EXPECTED_ORDER]
    in_order = all(
        order_positions[i][0] <= order_positions[i + 1][0]
        for i in range(len(order_positions) - 1)
    )
    return result(
        paragraph_labels=labels,
        expected_order=_EXPECTED_ORDER,
        detected_order=expected,
        in_order=in_order,
    )


def write_discussion(parameters: Any = None, **kwargs: Any) -> Any:
    """Legacy dispatcher compatible with scientific_writing.discussion_writing."""
    p = parameters if isinstance(parameters, dict) else kwargs
    findings = p.get("findings")
    if findings is None and p.get("principal_finding"):
        findings = [p["principal_finding"]] + (
            [p["interpretation"]] if p.get("interpretation") else []
        )
    prior_work = p.get("prior_work") or p.get("comparison_with_literature")
    limitations = p.get("limitations")
    implications = p.get("implications") or p.get("future_directions")
    conclusion = p.get("conclusion", "")
    rendered = render(findings=findings, prior_work=prior_work,
                      limitations=limitations, implications=implications,
                      conclusion=conclusion)
    return rendered["discussion"]


def run(operation: str = "run", **kwargs: Any) -> Any:
    params = unwrap(kwargs)
    if operation == "render":
        return render(**params)
    if operation == "paragraph_order_check":
        return paragraph_order_check(**params)
    if operation in ("run", "write_discussion"):
        return write_discussion(**params)
    raise ValueError(
        "Unknown operation %r. Available: ['render', 'paragraph_order_check', "
        "'run', 'write_discussion']" % operation
    )


register_skill("discussion_writing", run)
