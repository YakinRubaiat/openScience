"""Citation style formatting skill (deterministic).

Implements ``citation_styles``:

- ``format``: render a reference dict in vancouver / apa / ieee / harvard
  styles.
- ``in_text_marker``: produce the in-text marker for a reference — numbered
  styles (vancouver/ieee) return "[n]", author-year styles (apa/harvard)
  return "(Surname, year)".
"""

from __future__ import annotations

import re
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap

_STYLES = ("vancouver", "apa", "ieee", "harvard")


def _authors(ref: dict[str, Any]) -> list[str]:
    return [str(a) for a in (ref.get("authors") or [])]


def _surname(author: str) -> str:
    parts = author.replace(",", " ").split()
    return parts[0] if parts else author


def _initials(author: str) -> str:
    parts = author.replace(",", " ").split()
    return " ".join(p[0].upper() + "." for p in parts[1:] if p)


def _vancouver(ref: dict[str, Any]) -> str:
    authors = _authors(ref)
    if len(authors) > 6:
        author_str = ", ".join(authors[:6]) + ", et al"
    else:
        author_str = ", ".join(authors)
    title = str(ref.get("title", "")).rstrip(".")
    journal = str(ref.get("journal", ""))
    year = str(ref.get("year", ""))
    cite = f"{author_str}. {title}. {journal}. {year}."
    if ref.get("doi"):
        cite += f" doi:{ref['doi']}"
    return cite


def _apa(ref: dict[str, Any]) -> str:
    authors = _authors(ref)
    formatted = []
    for a in authors:
        surname = _surname(a)
        initials = _initials(a)
        formatted.append(f"{surname}, {initials}".rstrip(", "))
    if len(formatted) > 1:
        author_str = ", ".join(formatted[:-1]) + ", & " + formatted[-1]
    elif formatted:
        author_str = formatted[0]
    else:
        author_str = "Anonymous"
    year = str(ref.get("year", "n.d."))
    title = str(ref.get("title", "")).rstrip(".")
    journal = str(ref.get("journal", ""))
    cite = f"{author_str} ({year}). {title}. {journal}."
    if ref.get("doi"):
        cite += f" https://doi.org/{ref['doi']}"
    return cite


def _ieee(ref: dict[str, Any]) -> str:
    authors = _authors(ref)
    formatted = []
    for a in authors:
        surname = _surname(a)
        initials = _initials(a)
        formatted.append(f"{initials} {surname}".strip())
    if len(formatted) > 6:
        author_str = formatted[0] + " et al."
    else:
        author_str = ", ".join(formatted)
    title = str(ref.get("title", "")).rstrip(".")
    journal = str(ref.get("journal", ""))
    year = str(ref.get("year", ""))
    cite = f'{author_str}, "{title}," {journal}, {year}.'
    if ref.get("doi"):
        cite += f" doi: {ref['doi']}."
    return cite


def _harvard(ref: dict[str, Any]) -> str:
    authors = _authors(ref)
    formatted = []
    for a in authors:
        surname = _surname(a)
        initials = _initials(a)
        formatted.append(f"{surname}, {initials}".rstrip(", "))
    if len(formatted) > 3:
        author_str = formatted[0] + " et al."
    elif len(formatted) > 1:
        author_str = ", ".join(formatted[:-1]) + " and " + formatted[-1]
    elif formatted:
        author_str = formatted[0]
    else:
        author_str = "Anonymous"
    year = str(ref.get("year", "n.d."))
    title = str(ref.get("title", "")).rstrip(".")
    journal = str(ref.get("journal", ""))
    cite = f"{author_str} ({year}) '{title}', {journal}."
    if ref.get("doi"):
        cite += f" doi:{ref['doi']}"
    return cite


_FORMATTERS = {
    "vancouver": _vancouver,
    "apa": _apa,
    "ieee": _ieee,
    "harvard": _harvard,
}


def _author_year_marker(ref: dict[str, Any]) -> str:
    authors = _authors(ref)
    year = str(ref.get("year", "n.d."))
    if not authors:
        return f"(Anonymous, {year})"
    if len(authors) == 1:
        return f"({_surname(authors[0])}, {year})"
    if len(authors) == 2:
        return f"({_surname(authors[0])} and {_surname(authors[1])}, {year})"
    return f"({_surname(authors[0])} et al., {year})"


def format(reference: Any = None, style: str = "vancouver", **_: Any) -> dict[str, Any]:
    """Format a reference dict in the requested style."""
    style = (style or "vancouver").lower()
    formatter = _FORMATTERS.get(style)
    if formatter is None:
        raise ValueError(f"Unknown style {style!r}. Available: {sorted(_FORMATTERS)}")
    ref = reference if isinstance(reference, dict) else {}
    return result(style=style, citation=formatter(ref))


def in_text_marker(style: str = "vancouver", number: int = 1,
                   reference: Any = None, **_: Any) -> dict[str, Any]:
    """Return the in-text citation marker for ``style``.

    Numbered styles (vancouver, ieee) render as "[n]"; author-year styles
    (apa, harvard) render as "(Surname, year)".
    """
    style = (style or "vancouver").lower()
    if style not in _STYLES:
        raise ValueError(f"Unknown style {style!r}. Available: {_STYLES}")
    if style in ("vancouver", "ieee"):
        marker = f"[{int(number)}]"
        kind = "numbered"
    else:
        marker = _author_year_marker(reference if isinstance(reference, dict) else {})
        kind = "author-year"
    return result(style=style, marker=marker, kind=kind)


_OPERATIONS = {"format": format, "in_text_marker": in_text_marker}


def run(operation: str = "run", **kwargs: Any) -> Any:
    op = _OPERATIONS.get(operation) or _OPERATIONS["format"]
    if operation not in _OPERATIONS and operation != "run":
        raise ValueError(
            f"Unknown operation {operation!r}. Available: {sorted(_OPERATIONS)}"
        )
    return op(**unwrap(kwargs))


register_skill("citation_styles", run)
