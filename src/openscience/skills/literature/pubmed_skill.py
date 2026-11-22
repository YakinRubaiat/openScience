"""pubmed_api skill: thin wrapper over the PubMedConnector (lazy-imported)."""

from __future__ import annotations

from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap


def _connector():
    """Import the connector lazily so no network/deps are needed for import."""
    from openscience.connectors.papers.pubmed import get_connector

    return get_connector()


def search(**kwargs: Any) -> dict[str, Any]:
    """Search PubMed; returns parsed paper dicts."""
    kw = unwrap(kwargs)
    papers = _connector().search_and_fetch(
        query=kw.get("query") or "",
        max_results=int(kw.get("max_results", 20)),
        date_from=kw.get("date_from"),
        date_to=kw.get("date_to"),
    )
    return result(papers=[p.to_dict() for p in papers], count=len(papers))


def fetch_details(**kwargs: Any) -> dict[str, Any]:
    """Fetch full records for a list of PMIDs."""
    kw = unwrap(kwargs)
    pmids = kw.get("pmids") or []
    if isinstance(pmids, str):
        pmids = [p.strip() for p in pmids.split(",") if p.strip()]
    papers = _connector().fetch_details(pmids)
    return result(papers=[p.to_dict() for p in papers], count=len(papers))


def summary(**kwargs: Any) -> dict[str, Any]:
    """Summarize a list of paper dicts (pure — no network)."""
    papers = unwrap(kwargs).get("papers") or []
    return result(
        count=len(papers),
        years=sorted({p.get("year") for p in papers if p.get("year")}),
        journals=sorted({p.get("journal") for p in papers if p.get("journal")}),
    )


_OPS = {"search": search, "fetch_details": fetch_details, "summary": summary}


def run(operation: str = "run", **kwargs: Any) -> dict[str, Any]:
    """Dispatch to an operation; ``run`` defaults to ``search``."""
    op = _OPS.get(operation) or _OPS["search"]
    if operation not in _OPS and operation != "run":
        raise ValueError(f"Unknown operation {operation!r}. Available: {sorted(_OPS)}")
    return op(**kwargs)


register_skill("pubmed_api", run)
