"""pubmed_api skill: thin wrapper over the PubMedConnector."""

from typing import Any

from openscience.connectors.papers.pubmed import get_connector


def run(operation: str, **kwargs) -> Any:
    connector = get_connector()

    if operation == "search":
        query = kwargs.get("query") or ""
        max_results = int(kwargs.get("max_results", 100))
        date_from = kwargs.get("date_from")
        date_to = kwargs.get("date_to")
        papers = connector.search_and_fetch(
            query=query,
            max_results=max_results,
            date_from=date_from,
            date_to=date_to,
        )
        return [p.to_dict() for p in papers]

    if operation == "fetch":
        pmids = kwargs.get("pmids") or []
        return [p.to_dict() for p in connector.fetch_details(list(pmids))]

    raise ValueError(f"Unsupported operation: {operation}")
