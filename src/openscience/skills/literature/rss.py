"""rss_parsing skill: parse RSS/Atom feeds and filter entries by keywords."""

from __future__ import annotations

from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap


def parse(**kwargs: Any) -> dict[str, Any]:
    """Parse RSS/Atom XML text into a list of entry dicts (pure)."""
    kw = unwrap(kwargs)
    from openscience.connectors.papers.biorxiv import parse_rss

    xml_text = kw.get("xml") or kw.get("xml_text") or ""
    entries = parse_rss(xml_text)
    return result(entries=entries, count=len(entries))


def filter_keywords(**kwargs: Any) -> dict[str, Any]:
    """Keep entries whose title/description contains any keyword (pure)."""
    kw = unwrap(kwargs)
    entries = kw.get("entries") or []
    keywords = [k.lower() for k in (kw.get("keywords") or []) if k]
    matched = [
        e
        for e in entries
        if any(
            k in (e.get("title", "") + " " + e.get("description", "")).lower()
            for k in keywords
        )
    ]
    return result(entries=matched, count=len(matched))


_OPS = {"parse": parse, "filter_keywords": filter_keywords}


def run(operation: str = "run", **kwargs: Any) -> dict[str, Any]:
    """Dispatch to an operation; ``run`` defaults to ``parse``."""
    op = _OPS.get(operation) or _OPS["parse"]
    if operation not in _OPS and operation != "run":
        raise ValueError(f"Unknown operation {operation!r}. Available: {sorted(_OPS)}")
    return op(**kwargs)


register_skill("rss_parsing", run)
