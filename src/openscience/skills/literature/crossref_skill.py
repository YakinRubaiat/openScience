"""crossref_api skill: search Crossref works and parse raw JSON fixtures."""

from __future__ import annotations

from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap


def search(**kwargs: Any) -> dict[str, Any]:
    """Search Crossref works (network). Returns parsed items."""
    kw = unwrap(kwargs)
    from openscience.connectors.papers import crossref

    resp = crossref.works(query=kw.get("query") or "", rows=int(kw.get("rows", 20)))
    items = [crossref.parse_item(i) for i in (resp.get("message") or {}).get("items") or []]
    return result(items=items, count=len(items))


def get_work(**kwargs: Any) -> dict[str, Any]:
    """Fetch a single work by DOI (network). Returns parsed item."""
    kw = unwrap(kwargs)
    from openscience.connectors.papers import crossref

    resp = crossref.get_work(kw.get("doi") or "")
    item = crossref.parse_item(resp.get("message") or {})
    return result(item=item)


def parse_only(**kwargs: Any) -> dict[str, Any]:
    """Parse a provided Crossref item JSON dict (pure, no network)."""
    kw = unwrap(kwargs)
    from openscience.connectors.papers import crossref

    item = kw.get("item") or kw.get("json") or {}
    return result(item=crossref.parse_item(item))


_OPS = {"search": search, "get_work": get_work, "parse_only": parse_only}


def run(operation: str = "run", **kwargs: Any) -> dict[str, Any]:
    """Dispatch to an operation; ``run`` defaults to ``search``."""
    op = _OPS.get(operation) or _OPS["search"]
    if operation not in _OPS and operation != "run":
        raise ValueError(f"Unknown operation {operation!r}. Available: {sorted(_OPS)}")
    return op(**kwargs)


register_skill("crossref_api", run)
