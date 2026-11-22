"""Real PubMed connector using NCBI E-utilities API.

Free to use without an API key for <=3 requests/second.
See: https://www.ncbi.nlm.nih.gov/books/NBK25501/
"""

import time
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from typing import Optional
from urllib.parse import urlencode

import requests

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
DEFAULT_TOOL = "openscience"
DEFAULT_EMAIL = "openscience@example.org"
# Be polite: 3 req/s without API key
_MIN_INTERVAL = 0.34


@dataclass
class PubMedPaper:
    """Structured representation of a PubMed record."""

    pmid: str
    title: str
    abstract: str = ""
    authors: list[str] = field(default_factory=list)
    journal: str = ""
    pub_date: str = ""
    year: Optional[int] = None
    doi: str = ""
    mesh_terms: list[str] = field(default_factory=list)
    publication_types: list[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


class PubMedConnector:
    """Minimal real connector for NCBI PubMed via E-utilities."""

    def __init__(
        self,
        email: str = DEFAULT_EMAIL,
        tool: str = DEFAULT_TOOL,
        api_key: Optional[str] = None,
        session: Optional[requests.Session] = None,
    ):
        self.email = email
        self.tool = tool
        self.api_key = api_key
        self.session = session or requests.Session()
        self._last_request_at = 0.0

    # ---------- low-level ----------

    def _throttle(self):
        elapsed = time.time() - self._last_request_at
        wait = _MIN_INTERVAL - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_request_at = time.time()

    def _get(self, endpoint: str, **params) -> requests.Response:
        params.setdefault("tool", self.tool)
        params.setdefault("email", self.email)
        if self.api_key:
            params.setdefault("api_key", self.api_key)
        url = f"{EUTILS_BASE}/{endpoint}?{urlencode(params)}"
        self._throttle()
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        return resp

    # ---------- public API ----------

    def search(
        self,
        query: str,
        max_results: int = 100,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        sort: str = "relevance",
    ) -> list[str]:
        """Return a list of PMIDs matching the query.

        Args:
            query: PubMed query string (free text or fielded)
            max_results: cap on number of PMIDs to return
            date_from: YYYY/MM/DD or YYYY
            date_to: YYYY/MM/DD or YYYY
            sort: 'relevance' or 'date'
        """
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": sort,
        }
        if date_from or date_to:
            params["datetype"] = "pdat"
            if date_from:
                params["mindate"] = date_from
            if date_to:
                params["maxdate"] = date_to

        resp = self._get("esearch.fcgi", **params)
        data = resp.json()
        return data.get("esearchresult", {}).get("idlist", [])

    def fetch_details(self, pmids: list[str]) -> list[PubMedPaper]:
        """Fetch full records for the given PMIDs via efetch (XML)."""
        if not pmids:
            return []
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
        }
        resp = self._get("efetch.fcgi", **params)
        return self._parse_efetch_xml(resp.text)

    def search_and_fetch(
        self,
        query: str,
        max_results: int = 100,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        sort: str = "relevance",
    ) -> list[PubMedPaper]:
        """Search, then fetch all records. Convenience method."""
        pmids = self.search(
            query, max_results=max_results, date_from=date_from, date_to=date_to, sort=sort
        )
        # efetch works fine for ~200 PMIDs at once
        return self.fetch_details(pmids)

    # ---------- parsing ----------

    @staticmethod
    def _parse_efetch_xml(xml_text: str) -> list[PubMedPaper]:
        papers: list[PubMedPaper] = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return papers

        for article in root.findall(".//PubmedArticle"):
            pmid_el = article.find(".//MedlineCitation/PMID")
            if pmid_el is None or not pmid_el.text:
                continue
            pmid = pmid_el.text

            # Title
            title = ""
            title_el = article.find(".//ArticleTitle")
            if title_el is not None:
                title = "".join(title_el.itertext()).strip()

            # Abstract (may have multiple labeled sections)
            abstract_parts = []
            for ab in article.findall(".//Abstract/AbstractText"):
                label = ab.get("Label")
                text = "".join(ab.itertext()).strip()
                if label:
                    abstract_parts.append(f"{label}: {text}")
                elif text:
                    abstract_parts.append(text)
            abstract = "\n".join(abstract_parts).strip()

            # Authors
            authors = []
            for au in article.findall(".//AuthorList/Author"):
                last = au.findtext("LastName") or ""
                fore = au.findtext("ForeName") or ""
                coll = au.findtext("CollectiveName")
                if coll:
                    authors.append(coll.strip())
                elif last or fore:
                    authors.append(f"{last} {fore}".strip())

            # Journal
            journal = (
                article.findtext(".//Journal/Title")
                or article.findtext(".//Journal/ISOAbbreviation")
                or ""
            ).strip()

            # Pub date (Year-Month-Day; fall back to MedlineDate)
            pub_date = ""
            year = None
            pde = article.find(".//Journal/JournalIssue/PubDate")
            if pde is not None:
                y = pde.findtext("Year")
                m = pde.findtext("Month") or ""
                d = pde.findtext("Day") or ""
                if y and y.isdigit():
                    year = int(y)
                    pub_date = "-".join(p for p in [y, m, d] if p)
                else:
                    md = pde.findtext("MedlineDate") or ""
                    pub_date = md
                    # try to extract a 4-digit year
                    for tok in md.replace("-", " ").split():
                        if tok.isdigit() and len(tok) == 4:
                            year = int(tok)
                            break

            # DOI
            doi = ""
            for aid in article.findall(".//ArticleIdList/ArticleId"):
                if aid.get("IdType") == "doi" and aid.text:
                    doi = aid.text.strip()
                    break

            # MeSH terms
            mesh_terms = [
                (m.findtext("DescriptorName") or "").strip()
                for m in article.findall(".//MeshHeading")
            ]
            mesh_terms = [t for t in mesh_terms if t]

            # Publication types
            pub_types = [
                (pt.text or "").strip()
                for pt in article.findall(".//PublicationType")
            ]
            pub_types = [t for t in pub_types if t]

            papers.append(
                PubMedPaper(
                    pmid=pmid,
                    title=title,
                    abstract=abstract,
                    authors=authors,
                    journal=journal,
                    pub_date=pub_date,
                    year=year,
                    doi=doi,
                    mesh_terms=mesh_terms,
                    publication_types=pub_types,
                )
            )

        return papers


# Singleton used by the skill layer
_default_connector: Optional[PubMedConnector] = None


def get_connector() -> PubMedConnector:
    global _default_connector
    if _default_connector is None:
        _default_connector = PubMedConnector()
    return _default_connector
