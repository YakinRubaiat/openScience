"""Extractive text summarization skill (deterministic, no LLM).

Implements ``text_summarization`` with a classic frequency-plus-position
sentence scorer: sentences are scored by the sum of normalized term
frequencies of their content words, boosted for appearing early in the
source text. The top-n sentences are returned in original document order
so the summary reads coherently. A ``word_limit_trim`` operation truncates
text at a sentence boundary near the limit.
"""

from __future__ import annotations

import re
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap

_STOPWORDS = frozenset(
    "a an the and or but if then of in on at to for with by from as is are was were "
    "be been being it its this that these those we they he she i you not no do does did "
    "have has had will would can could should may might than so such into over under"
    .split()
)


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w[\w'-]*\b", text))


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in parts if s.strip()]


def _term_frequencies(sentences: list[str]) -> dict[str, float]:
    counts: dict[str, int] = {}
    for s in sentences:
        for w in re.findall(r"\b[a-zA-Z][a-zA-Z'-]*\b", s.lower()):
            if w not in _STOPWORDS:
                counts[w] = counts.get(w, 0) + 1
    if not counts:
        return {}
    max_count = max(counts.values())
    return {w: c / max_count for w, c in counts.items()}


def _score_sentences(sentences: list[str]) -> list[float]:
    tf = _term_frequencies(sentences)
    scores: list[float] = []
    n = max(len(sentences), 1)
    for i, s in enumerate(sentences):
        words = [w for w in re.findall(r"\b[a-zA-Z][a-zA-Z'-]*\b", s.lower())
                 if w not in _STOPWORDS]
        # sum of term frequencies with mild length normalization (sqrt), so
        # information-dense sentences beat short ones; small position boost
        # for early sentences breaks ties toward the lead.
        freq_score = sum(tf.get(w, 0.0) for w in words) / max(len(words) ** 0.5, 1)
        position_score = 1.0 - (i / n)
        scores.append(freq_score + 0.2 * position_score)
    return scores


def extractive(text: str = "", num_sentences: int = 3, **_: Any) -> dict[str, Any]:
    """Return the top-``num_sentences`` sentences in original document order."""
    sentences = _sentences(text)
    if not sentences:
        return result(summary="", sentences=[], word_count=0, num_sentences=0)
    n = max(1, min(int(num_sentences), len(sentences)))
    scores = _score_sentences(sentences)
    ranked = sorted(range(len(sentences)), key=lambda i: scores[i], reverse=True)
    chosen = sorted(ranked[:n])
    picked = [sentences[i] for i in chosen]
    summary = " ".join(picked)
    return result(
        summary=summary,
        sentences=picked,
        selected_indices=chosen,
        word_count=_word_count(summary),
        num_sentences=len(picked),
    )


def word_limit_trim(text: str = "", word_limit: int = 100, **_: Any) -> dict[str, Any]:
    """Trim ``text`` to at most ``word_limit`` words, ending at a sentence boundary."""
    words = text.split()
    if len(words) <= word_limit:
        return result(text=text, word_count=len(words), word_limit=word_limit,
                      trimmed=False)
    trimmed = " ".join(words[:word_limit])
    last_period = trimmed.rfind(".")
    if last_period > len(trimmed) * 0.5:
        trimmed = trimmed[: last_period + 1]
    return result(text=trimmed, word_count=_word_count(trimmed),
                  word_limit=word_limit, trimmed=True)


_OPERATIONS = {
    "extractive": extractive,
    "word_limit_trim": word_limit_trim,
}


def run(operation: str = "run", **kwargs: Any) -> Any:
    op = _OPERATIONS.get(operation) or _OPERATIONS["extractive"]
    if operation not in _OPERATIONS and operation != "run":
        raise ValueError(
            f"Unknown operation {operation!r}. Available: {sorted(_OPERATIONS)}"
        )
    return op(**unwrap(kwargs))


register_skill("text_summarization", run)
