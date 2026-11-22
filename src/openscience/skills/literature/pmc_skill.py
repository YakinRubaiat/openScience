"""pmc_api skill: search PMC, fetch full text XML, and parse JATS fixtures."""

from __future__ import annotations

from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap


def search(**kwargs: Any) -> dict[str, Any]:
    """E-utilities esearch on the ``pmc`` db (network). Returns id list."""
    kw = unwrap(kwargs)
    from openscience.connectors.papers import pmc

    resp = pmc.search(query=kw.get("query") or "", retmax=int(kw.get("retmax", 25)))
    ids = (resp.get("esearchresult") or {}).get("idlist") or []
    return result(ids=ids, count=len(ids))


def fetch_fulltext(**kwargs: Any) -> dict[str, Any]:
    """Fetch and parse full text XML for one PMCID (network)."""
    kw = unwrap(kwargs)
    from openscience.connectors.papers import pmc

    xml_text = pmc.fetch_fulltext_xml(kw.get("pmcid") or "")
    parsed = pmc.parse_fulltext(xml_text)
    return result(**parsed)


def parse_only(**kwargs: Any) -> dict[str, Any]:
    """Parse a provided JATS XML string (pure, no network)."""
    kw = unwrap(kwargs)
    from openscience.connectors.papers import pmc

    xml_text = kw.get("xml") or kw.get("xml_text") or ""
    return result(**pmc.parse_fulltext(xml_text))


_OPS = {"search": search, "fetch_fulltext": fetch_fulltext, "parse_only": parse_only}


def run(operation: str = "run", **kwargs: Any) -> dict[str, Any]:
    """Dispatch to an operation; ``run`` defaults to ``search``."""
    op = _OPS.get(operation) or _OPS["search"]
    if operation not in _OPS and operation != "run":
        raise ValueError(f"Unknown operation {operation!r}. Available: {sorted(_OPS)}")
    return op(**kwargs)


register_skill("pmc_api", run)
