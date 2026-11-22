"""Journal manuscript template skill (deterministic).

Implements ``journal_templates``:

- ``get_template``: return the built-in template for a journal family
  (nature / plos / ieee / generic): ordered sections, abstract word limit and
  overall word limit.
- ``format_check``: check a manuscript dict (section name -> text) against a
  template: missing sections, out-of-order sections, word-limit violations.
"""

from __future__ import annotations

import re
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap

_TEMPLATES: dict[str, dict[str, Any]] = {
    "nature": {
        "name": "nature",
        "sections": ["abstract", "introduction", "results", "discussion",
                     "methods", "references"],
        "abstract_word_limit": 200,
        "word_limit": 5000,
    },
    "plos": {
        "name": "plos",
        "sections": ["abstract", "introduction", "materials_and_methods",
                     "results", "discussion", "references"],
        "abstract_word_limit": 300,
        "word_limit": 10000,
    },
    "ieee": {
        "name": "ieee",
        "sections": ["abstract", "introduction", "methods", "results",
                     "discussion", "conclusion", "references"],
        "abstract_word_limit": 250,
        "word_limit": 8000,
    },
    "generic": {
        "name": "generic",
        "sections": ["abstract", "introduction", "methods", "results",
                     "discussion", "conclusion", "references"],
        "abstract_word_limit": 250,
        "word_limit": 7000,
    },
}


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w[\w'-]*\b", text))


def get_template(journal: str = "generic", **_: Any) -> dict[str, Any]:
    """Return the built-in template for ``journal`` (falls back to generic)."""
    key = (journal or "generic").lower()
    template = _TEMPLATES.get(key, _TEMPLATES["generic"])
    return result(**{k: v for k, v in template.items()},
                  available=sorted(_TEMPLATES))


def format_check(manuscript: Any = None, journal: str = "generic", **_: Any) -> dict[str, Any]:
    """Check a manuscript (dict of section name -> text) against a template."""
    tpl = get_template(journal)
    manuscript = manuscript if isinstance(manuscript, dict) else {}
    normalized = {str(k).lower().replace(" ", "_"): str(v)
                  for k, v in manuscript.items()}

    expected = tpl["sections"]
    present = [s for s in expected if s in normalized and normalized[s].strip()]
    missing = [s for s in expected if s not in present]

    ordered = [s for s in normalized if s in expected]
    in_order = ordered == sorted(ordered, key=expected.index)

    violations: list[str] = []
    abstract = normalized.get("abstract", "")
    n_abstract = _word_count(abstract)
    if n_abstract > tpl["abstract_word_limit"]:
        violations.append(
            f"abstract exceeds {tpl['abstract_word_limit']} words ({n_abstract})"
        )
    total = sum(_word_count(t) for t in normalized.values())
    if total > tpl["word_limit"]:
        violations.append(f"manuscript exceeds {tpl['word_limit']} words ({total})")
    if not in_order:
        violations.append("sections out of template order")

    return result(
        journal=tpl["name"],
        sections_expected=expected,
        sections_present=present,
        sections_missing=missing,
        sections_in_order=in_order,
        abstract_word_count=n_abstract,
        word_count=total,
        violations=violations,
        compliant=not missing and not violations,
    )


_OPERATIONS = {"get_template": get_template, "format_check": format_check}


def run(operation: str = "run", **kwargs: Any) -> Any:
    op = _OPERATIONS.get(operation) or _OPERATIONS["get_template"]
    if operation not in _OPERATIONS and operation != "run":
        raise ValueError(
            f"Unknown operation {operation!r}. Available: {sorted(_OPERATIONS)}"
        )
    return op(**unwrap(kwargs))


register_skill("journal_templates", run)
