"""Template-engine backed scientific writing skill.

Implements the ``scientific_writing``, ``results_writing`` and
``discussion_writing`` skills used by the writing agents. Since no LLM API
key is configured in this environment, these skills compose manuscript text
from structured research content using disciplined, journal-style templates
(IMRaD structure, hedged claims, past-tense methods, present-tense
interpretation).

The entry point for each skill is ``run(operation=..., **kwargs)``.
"""

from __future__ import annotations

import re
from typing import Any

from openscience.skills import register_skill

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w[\w'-]*\b", text))


def _trim_to_limit(text: str, word_limit: int) -> str:
    words = text.split()
    if len(words) <= word_limit:
        return text
    trimmed = " ".join(words[:word_limit])
    # end at a sentence boundary if possible
    last_period = trimmed.rfind(".")
    if last_period > len(trimmed) * 0.6:
        trimmed = trimmed[: last_period + 1]
    return trimmed


def _fmt(p: dict[str, Any], key: str, default: str = "") -> str:
    val = p.get(key)
    if val is None or val == "":
        return default
    return str(val)


def _end_period(text: str) -> str:
    """Ensure ``text`` ends with terminal punctuation."""
    text = text.rstrip()
    if text and text[-1] not in ".!?":
        return text + "."
    return text


# ---------------------------------------------------------------------------
# abstract
# ---------------------------------------------------------------------------

ABSTRACT_TEMPLATE = """\
{background} {gap} {aim} {methods} {results} {conclusion}"""


def _write_abstract(content: Any, journal: str, word_limit: int) -> dict[str, Any]:
    """Compose a structured abstract from paper_content.

    ``content`` may be a dict with keys background/gap/aim/methods/results/
    conclusion, or a raw string (returned trimmed to the word limit).
    """
    if isinstance(content, str):
        abstract = _trim_to_limit(content, word_limit)
        return {
            "abstract": abstract,
            "word_count": _word_count(abstract),
            "word_limit": word_limit,
            "journal": journal,
        }

    c = content or {}
    parts = [
        _fmt(c, "background"),
        _fmt(c, "gap"),
        _fmt(c, "aim"),
        _fmt(c, "methods"),
        _fmt(c, "results"),
        _fmt(c, "conclusion"),
    ]
    abstract = " ".join(_end_period(part) for part in parts if part)
    abstract = re.sub(r"\s+", " ", abstract).strip()
    abstract = _trim_to_limit(abstract, word_limit)
    return {
        "abstract": abstract,
        "word_count": _word_count(abstract),
        "word_limit": word_limit,
        "journal": journal,
        "structure": ["background", "gap", "aim", "methods", "results", "conclusion"],
    }


# ---------------------------------------------------------------------------
# introduction
# ---------------------------------------------------------------------------

INTRO_TEMPLATE = """\
{para1_field}

{para2_gap}

{para3_aim}
"""


def _write_introduction(params: dict[str, Any]) -> str:
    p = params or {}
    field = _fmt(p, "field", "this research area")
    known = _fmt(p, "established_knowledge")
    gap = _fmt(p, "knowledge_gap")
    significance = _fmt(p, "significance")
    aim = _fmt(p, "aim")
    approach = _fmt(p, "approach")
    finding = _fmt(p, "principal_finding")

    para1 = (
        f"{known}"
        if known
        else f"{field} has been the focus of sustained investigation over the past decades, "
        f"and a substantial body of work now defines its conceptual and methodological foundations."
    )
    para2 = (
        _end_period(f"However, {gap}") if gap else "However, important questions remain unresolved."
    )
    if significance:
        para2 += " " + _end_period(f"Addressing this gap is significant because {significance}")
    para3 = (
        _end_period(f"Here, we set out to {aim}")
        if aim
        else "Here, we describe a study designed to address this question."
    )
    if approach:
        para3 += " " + _end_period(f"To this end, {approach}")
    if finding:
        para3 += " " + _end_period(f"We show that {finding}")

    return INTRO_TEMPLATE.format(para1_field=para1, para2_gap=para2, para3_aim=para3).strip()


# ---------------------------------------------------------------------------
# methods
# ---------------------------------------------------------------------------


def _write_methods(result: Any, journal: str, citation_format: str) -> str:
    """Render a methods section from an analysis_result structure."""
    if isinstance(result, str):
        return result
    # Accept framework ``Result`` objects as well as raw dict payloads.
    r = getattr(result, "data", None) if result is not None else None
    if not isinstance(r, dict):
        r = result if isinstance(result, dict) else {}
    paragraphs: list[str] = []

    if design := r.get("study_design"):
        paragraphs.append(f"Study design. {design}")
    if model := r.get("model_system"):
        paragraphs.append(f"Model system. {model}")
    if compounds := r.get("compounds"):
        paragraphs.append(f"Compounds and reagents. {compounds}")
    if assays := r.get("assays"):
        paragraphs.append(f"Assays. {assays}")
    if stats := r.get("statistics"):
        paragraphs.append(f"Statistical analysis. {stats}")
    if not paragraphs:
        paragraphs.append("Methods were not provided in structured form.")

    return "\n\n".join(paragraphs)


# ---------------------------------------------------------------------------
# results
# ---------------------------------------------------------------------------


def _write_results(params: dict[str, Any]) -> str:
    p = params or {}
    findings = p.get("findings") or []
    if isinstance(findings, str):
        return findings
    paragraphs = []
    for f in findings:
        if isinstance(f, dict):
            headline = f.get("headline", "")
            detail = f.get("detail", "")
            stat = f.get("statistic", "")
            text = headline
            if detail:
                text += f" {detail}"
            if stat:
                text += f" ({stat})"
            paragraphs.append(text.strip())
        else:
            paragraphs.append(str(f))
    return "\n\n".join(paragraphs).strip()


# ---------------------------------------------------------------------------
# discussion
# ---------------------------------------------------------------------------


def _write_discussion(params: dict[str, Any]) -> str:
    p = params or {}
    principal = _fmt(p, "principal_finding")
    interpretation = _fmt(p, "interpretation")
    comparison = _fmt(p, "comparison_with_literature")
    mechanism = _fmt(p, "mechanistic_insight")
    limitations = p.get("limitations") or []
    if isinstance(limitations, str):
        limitations = [limitations]
    future = _fmt(p, "future_directions")
    conclusion = _fmt(p, "conclusion")

    paras = []
    if principal:
        sentence = _end_period(f"In this study, {principal}")
        if interpretation:
            sentence += " " + _end_period(interpretation)
        paras.append(sentence)
    if comparison:
        paras.append(_end_period(comparison))
    if mechanism:
        paras.append(_end_period(f"Mechanistically, {mechanism}"))
    if limitations:
        items = [_end_period(f) for f in limitations]
        paras.append("Our study has limitations. " + " ".join(items))
    if future:
        paras.append(_end_period(future))
    if conclusion:
        paras.append(_end_period(f"In conclusion, {conclusion}"))
    return "\n\n".join(paras).strip()


# ---------------------------------------------------------------------------
# skill entry points
# ---------------------------------------------------------------------------


def scientific_writing(operation: str, **kwargs) -> Any:
    if operation == "write_abstract":
        return _write_abstract(
            kwargs.get("content", {}),
            journal=kwargs.get("journal", "general"),
            word_limit=int(kwargs.get("word_limit", 250)),
        )
    if operation == "write_methods":
        return _write_methods(
            kwargs.get("result"),
            journal=kwargs.get("journal", "nature"),
            citation_format=kwargs.get("citation_format", "apa"),
        )
    if operation == "write_introduction" or operation == "run":
        return _write_introduction(kwargs.get("parameters") or kwargs)
    raise ValueError(f"Unsupported scientific_writing operation: {operation}")


def results_writing(operation: str, **kwargs) -> Any:
    if operation in ("run", "write_results"):
        return _write_results(kwargs.get("parameters") or kwargs)
    raise ValueError(f"Unsupported results_writing operation: {operation}")


def discussion_writing(operation: str, **kwargs) -> Any:
    if operation in ("run", "write_discussion"):
        return _write_discussion(kwargs.get("parameters") or kwargs)
    raise ValueError(f"Unsupported discussion_writing operation: {operation}")


register_skill("scientific_writing", scientific_writing)
register_skill("results_writing", results_writing)
register_skill("discussion_writing", discussion_writing)
