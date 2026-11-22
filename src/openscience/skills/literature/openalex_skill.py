"""openalex_api skill: search OpenAlex works and parse raw JSON fixtures."""

from __future__ import annotations

from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap


def search(**kwargs: Any) -> dict[str, Any]:
    """Search OpenAlex works (network). Returns parsed works."""
    kw = unwrap(kwargs)
    from openscience.connectors.papers import openalex

    resp = openalex.search_works(
        query=kw.get("query") or "",
        per_page=int(kw.get("per_page", 25)),
        filters=kw.get("filters"),
    )
    works = [openalex.parse_work(w) for w in resp.get("results") or []]
    return result(works=works, count=len(works), total=resp.get("meta", {}).get("count"))


def parse_only(**kwargs: Any) -> dict[str, Any]:
    """Parse a provided OpenAlex work JSON dict (pure, no network)."""
    kw = unwrap(kwargs)
    from openscience.connectors.papers import openalex

    work = kw.get("work") or kw.get("json") or {}
    return result(work=openalex.parse_work(work))


def works_from_dict(**kwargs: Any) -> dict[str, Any]:
    """Parse a full OpenAlex API response dict into a list of works (pure)."""
    kw = unwrap(kwargs)
    from openscience.connectors.papers import openalex

    resp = kw.get("response") or {}
    works = [openalex.parse_work(w) for w in resp.get("results") or []]
    return result(works=works, count=len(works))


_OPS = {"search": search, "parse_only": parse_only, "works_from_dict": works_from_dict}


def run(operation: str = "run", **kwargs: Any) -> dict[str, Any]:
    """Dispatch to an operation; ``run`` defaults to ``search``."""
    op = _OPS.get(operation) or _OPS["search"]
    if operation not in _OPS and operation != "run":
        raise ValueError(f"Unknown operation {operation!r}. Available: {sorted(_OPS)}")
    return op(**kwargs)


register_skill("openalex_api", run)
