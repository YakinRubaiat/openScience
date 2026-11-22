"""PubMed Central connector (NCBI E-utilities, ``pmc`` db) via stdlib urllib.

Network functions (``search``, ``fetch_fulltext_xml``) are thin wrappers;
``parse_fulltext`` is pure and testable offline.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
USER_AGENT = "openscience/0.1 (mailto:openscience@example.org)"
_TIMEOUT = 30


def _request(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=_TIMEOUT) as resp:  # noqa: S310 - public API
            return resp.read()
    except HTTPError as exc:
        raise RuntimeError(f"PMC API error {exc.code} for {url}: {exc.reason}") from exc
    except (URLError, OSError) as exc:
        raise RuntimeError(f"PMC API request failed for {url}: {exc}") from exc


def search(query: str, retmax: int = 25) -> dict[str, Any]:
    """E-utilities esearch on the ``pmc`` db. Returns raw JSON response."""
    url = f"{EUTILS_BASE}/esearch.fcgi?{urlencode({'db': 'pmc', 'term': query, 'retmax': retmax, 'retmode': 'json'})}"
    return json.loads(_request(url).decode("utf-8"))


def fetch_fulltext_xml(pmcid: str) -> str:
    """E-utilities efetch full text XML for one PMC id (e.g. ``PMC7096803``)."""
    url = f"{EUTILS_BASE}/efetch.fcgi?{urlencode({'db': 'pmc', 'id': pmcid, 'retmode': 'xml'})}"
    return _request(url).decode("utf-8")


def parse_fulltext(xml_text: str) -> dict[str, Any]:
    """Parse JATS article XML into title, abstract, sections, refs count.

    Pure function: works entirely on the given XML string.
    """
    out: dict[str, Any] = {"title": "", "abstract_text": "", "sections": [], "refs_count": 0}
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return out

    title_el = root.find(".//article-title")
    if title_el is not None:
        out["title"] = "".join(title_el.itertext()).strip()

    abstract_el = root.find(".//abstract")
    if abstract_el is not None:
        out["abstract_text"] = " ".join("".join(abstract_el.itertext()).split())

    for sec in root.findall(".//body//sec"):
        heading_el = sec.find("./title")
        heading = "".join(heading_el.itertext()).strip() if heading_el is not None else ""
        # direct paragraphs only (not nested sec text)
        texts = []
        for child in sec:
            if child.tag in ("p",):
                texts.append("".join(child.itertext()).strip())
        out["sections"].append({"heading": heading, "text": "\n".join(t for t in texts if t)})

    out["refs_count"] = len(root.findall(".//ref-list/ref"))
    return out
