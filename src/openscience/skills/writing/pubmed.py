"""PubMed skill backed by NCBI E-utilities (free, no API key required).

Implements ``pubmed_api`` with a real ``search`` operation that queries
PubMed via esearch/esummary/efetch over HTTPS.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

import requests

from openscience.skills import register_skill

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_TIMEOUT = 20


def _esearch(query: str, max_results: int) -> list[str]:
    r = requests.get(
        f"{EUTILS}/esearch.fcgi",
        params={
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance",
        },
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
    return r.json().get("esearchresult", {}).get("idlist", [])


def _efetch_details(pmids: list[str]) -> list[dict[str, Any]]:
    if not pmids:
        return []
    r = requests.get(
        f"{EUTILS}/efetch.fcgi",
        params={"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"},
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
    root = ET.fromstring(r.text)
    papers: list[dict[str, Any]] = []
    for art in root.findall(".//PubmedArticle"):
        pmid_el = art.find(".//PMID")
        title_el = art.find(".//ArticleTitle")
        journal_el = art.find(".//Journal/Title")
        year_el = art.find(".//JournalIssue/PubDate/Year")
        if year_el is None:
            year_el = art.find(".//JournalIssue/PubDate/MedlineDate")
        authors = []
        for a in art.findall(".//AuthorList/Author"):
            last = a.findtext("LastName")
            initials = a.findtext("Initials")
            if last:
                authors.append(f"{last} {initials or ''}".strip())
        abstract_parts = [(t.text or "") for t in art.findall(".//Abstract/AbstractText")]
        doi = None
        for id_el in art.findall(".//ArticleIdList/ArticleId"):
            if id_el.get("IdType") == "doi":
                doi = id_el.text
        papers.append(
            {
                "pmid": pmid_el.text if pmid_el is not None else None,
                "title": (title_el.text or "").strip() if title_el is not None else "",
                "journal": journal_el.text if journal_el is not None else "",
                "year": (year_el.text or "")[:4] if year_el is not None else "",
                "authors": authors,
                "abstract": " ".join(p for p in abstract_parts if p).strip(),
                "doi": doi,
            }
        )
    return papers


def pubmed_api(operation: str, **kwargs) -> Any:
    if operation == "search":
        query = kwargs.get("query", "")
        max_results = int(kwargs.get("max_results", 10))
        pmids = _esearch(query, max_results)
        return _efetch_details(pmids)
    if operation == "fetch":
        pmids = kwargs.get("pmids") or []
        return _efetch_details(list(pmids))
    raise ValueError(f"Unsupported pubmed_api operation: {operation}")


register_skill("pubmed_api", pubmed_api)
