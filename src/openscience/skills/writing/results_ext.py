"""Extended results-writing skill (deterministic templates).

Implements ``results_writing_ext``:

- ``render_with_stats``: given findings (strings or dicts with headline /
  detail / statistic) compose a Results paragraph where each finding's
  statistical string is attached parenthetically.
- ``table_reference_inserter``: insert ``(Table n)`` references into a text
  after the first sentence mentioning each supplied table keyword.
"""

from __future__ import annotations

import re
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w[\w'-]*\b", text))


def _render_finding(f: Any) -> str:
    if isinstance(f, dict):
        headline = str(f.get("headline", "")).strip()
        detail = str(f.get("detail", "")).strip()
        stat = str(f.get("statistic", "")).strip()
        text = headline
        if detail:
            text = f"{text} {detail}".strip()
        if stat:
            text = f"{text} ({stat})".strip()
        return text
    return str(f).strip()


def render_with_stats(findings: Any = None, **_: Any) -> dict[str, Any]:
    """Compose a Results paragraph from findings with statistic strings."""
    if isinstance(findings, str):
        return result(paragraph=findings, findings=[findings],
                      word_count=_word_count(findings))
    items = [f for f in (findings or [])]
    lines = [(_render_finding(f)) for f in items if _render_finding(f)]
    paragraph = " ".join(
        line if line.endswith((".", "!", "?")) else line + "." for line in lines
    )
    return result(paragraph=paragraph, findings=lines,
                  word_count=_word_count(paragraph))


def table_reference_inserter(text: str = "", tables: Any = None, **_: Any) -> dict[str, Any]:
    """Insert ``(Table n)`` after the first sentence mentioning each keyword.

    ``tables`` is a list of dicts like ``{"number": 1, "keyword": "demographics"}``
    or a list of plain keyword strings (numbered from 1).
    """
    specs: list[tuple[int, str]] = []
    for i, t in enumerate(tables or []):
        if isinstance(t, dict):
            specs.append((int(t.get("number", i + 1)), str(t.get("keyword", ""))))
        else:
            specs.append((i + 1, str(t)))

    inserted: list[int] = []
    out = text
    for number, keyword in sorted(specs, key=lambda s: s[0]):
        if not keyword:
            continue
        if f"Table {number}" in out:
            continue
        # find first sentence containing the keyword
        sentences = re.split(r"(?<=[.!?])\s+", out)
        for idx, sentence in enumerate(sentences):
            if re.search(re.escape(keyword), sentence, re.IGNORECASE):
                stripped = sentence.rstrip()
                end = stripped[-1] if stripped.endswith((".", "!", "?")) else ""
                core = stripped[:-1] if end else stripped
                sentences[idx] = f"{core} (Table {number}){end}"
                inserted.append(number)
                out = " ".join(sentences)
                break
    return result(text=out, inserted=inserted, tables_referenced=len(inserted))


_OPERATIONS = {
    "render_with_stats": render_with_stats,
    "table_reference_inserter": table_reference_inserter,
    "run": render_with_stats,
}


def run(operation: str = "run", **kwargs: Any) -> Any:
    op = _OPERATIONS.get(operation) or _OPERATIONS["render_with_stats"]
    if operation not in _OPERATIONS:
        raise ValueError(
            f"Unknown operation {operation!r}. Available: {sorted(_OPERATIONS)}"
        )
    return op(**unwrap(kwargs))


register_skill("results_writing_ext", run)
