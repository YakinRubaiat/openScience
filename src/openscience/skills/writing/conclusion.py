"""Conclusion writing skill (deterministic templates).

Implements ``conclusion_writing``:

- ``render``: summary + impact + future -> a compact conclusion paragraph.
- ``word_count``: count words in a conclusion draft (regex-based tokenizer).
"""

from __future__ import annotations

import re
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w[\w'-]*\b", text))


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


def render(summary: Any = None, impact: str = "", future: Any = None,
           word_limit: int = 150, **_: Any) -> dict[str, Any]:
    """Compose a Conclusion from summary, impact, and future directions."""
    sentences: list[str] = []

    summary_items = _as_list(summary)
    if summary_items:
        body = " ".join(_end_period(s) for s in summary_items)
        sentences.append(_end_period(f"In summary, {body}"))

    if impact:
        sentences.append(_end_period(f"These findings {impact}"))

    future_items = _as_list(future)
    if future_items:
        body = " ".join(_end_period(f) for f in future_items)
        sentences.append(_end_period(f"Future work should {body}"))

    if not sentences:
        sentences.append("No conclusion content was provided.")

    conclusion = " ".join(sentences)
    words = conclusion.split()
    trimmed = False
    if len(words) > word_limit:
        text = " ".join(words[:word_limit])
        last_period = text.rfind(".")
        conclusion = text[: last_period + 1] if last_period > len(text) * 0.5 else text
        trimmed = True

    return result(
        conclusion=conclusion,
        word_count=_word_count(conclusion),
        word_limit=word_limit,
        trimmed=trimmed,
    )


def word_count(text: str = "", **_: Any) -> dict[str, Any]:
    """Count words in a conclusion draft."""
    return result(word_count=_word_count(text))


_OPERATIONS = {"render": render, "word_count": word_count}


def run(operation: str = "run", **kwargs: Any) -> Any:
    op = _OPERATIONS.get(operation) or _OPERATIONS["render"]
    if operation not in _OPERATIONS and operation != "run":
        raise ValueError(
            f"Unknown operation {operation!r}. Available: {sorted(_OPERATIONS)}"
        )
    return op(**unwrap(kwargs))


register_skill("conclusion_writing", run)
