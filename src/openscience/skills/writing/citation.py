"""Citation / BibTeX skill.

Implements the ``bibtex`` skill used by the citation_manager agent:
formatting PubMed-style reference dicts into numbered citations (Vancouver /
APA) and BibTeX entries.
"""

from __future__ import annotations

from typing import Any

from openscience.skills import register_skill


def _to_bibtex_key(ref: dict[str, Any]) -> str:
    first_author = (ref.get("authors") or ["anon"])[0].split()[0].lower()
    year = ref.get("year") or "nd"
    word = (ref.get("title", "untitled").split() or ["untitled"])[0].lower()
    word = "".join(ch for ch in word if ch.isalnum())
    return f"{first_author}{year}{word}"


def _vancouver(ref: dict[str, Any]) -> str:
    authors = ref.get("authors") or []
    if len(authors) > 6:
        author_str = ", ".join(authors[:6]) + ", et al"
    else:
        author_str = ", ".join(authors)
    year = ref.get("year", "")
    title = ref.get("title", "").rstrip(".")
    journal = ref.get("journal", "")
    doi = ref.get("doi")
    cite = f"{author_str}. {title}. {journal}. {year}."
    if doi:
        cite += f" doi:{doi}"
    elif ref.get("pmid"):
        cite += f" PMID:{ref['pmid']}"
    return cite


def _apa(ref: dict[str, Any]) -> str:
    authors = ref.get("authors") or []
    author_str = ", ".join(authors)
    year = ref.get("year", "n.d.")
    title = ref.get("title", "").rstrip(".")
    journal = ref.get("journal", "")
    cite = f"{author_str} ({year}). {title}. {journal}."
    if ref.get("doi"):
        cite += f" https://doi.org/{ref['doi']}"
    return cite


def _bibtex(ref: dict[str, Any]) -> str:
    authors = " and ".join(ref.get("authors") or ["Anonymous"])
    lines = [
        f"@article{{{_to_bibtex_key(ref)},",
        f"  author = {{{authors}}},",
        f"  title = {{{ref.get('title', 'Untitled')}}},",
        f"  journal = {{{ref.get('journal', '')}}},",
        f"  year = {{{ref.get('year', '')}}},",
    ]
    if ref.get("doi"):
        lines.append(f"  doi = {{{ref['doi']}}},")
    if ref.get("pmid"):
        lines.append(f"  note = {{PMID: {ref['pmid']}}},")
    lines.append("}")
    return "\n".join(lines)


def bibtex(operation: str, **kwargs) -> Any:
    params = kwargs.get("parameters") or kwargs
    refs = params.get("references") or []
    style = params.get("style", "vancouver")

    formatter = _vancouver if style == "vancouver" else _apa
    formatted = [formatter(r) for r in refs]
    numbered = [f"{i + 1}. {f}" for i, f in enumerate(formatted)]
    bib_entries = [_bibtex(r) for r in refs]

    return {
        "formatted_citations": numbered,
        "bibtex": "\n\n".join(bib_entries),
        "count": len(refs),
        "style": style,
    }


register_skill("bibtex", bibtex)
