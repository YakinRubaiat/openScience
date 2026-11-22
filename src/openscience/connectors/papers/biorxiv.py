"""bioRxiv/medRxiv connector (https://api.biorxiv.org) using stdlib urllib only.

Network functions (``fetch_details``) are thin wrappers; all parsing
(``parse_record``, ``parse_rss``) is pure and testable offline.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = "https://api.biorxiv.org/details"
USER_AGENT = "openscience/0.1 (mailto:openscience@example.org)"
_TIMEOUT = 30


def fetch_details(
    server: str, date_from: str, date_to: str, cursor: int = 0
) -> dict[str, Any]:
    """Fetch preprint details for ``server`` ('biorxiv' or 'medrxiv') posted
    between ``date_from`` and ``date_to`` (YYYY-MM-DD). Returns raw JSON.
    """
    url = f"{BASE_URL}/{server}/{date_from}/{date_to}/{cursor}"
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=_TIMEOUT) as resp:  # noqa: S310 - public API
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"bioRxiv API error {exc.code} for {url}: {exc.reason}") from exc
    except (URLError, OSError) as exc:
        raise RuntimeError(f"bioRxiv API request failed for {url}: {exc}") from exc


def parse_record(json: dict[str, Any]) -> dict[str, Any]:
    """Parse one bioRxiv detail record into a flat dict."""
    return {
        "doi": json.get("doi") or "",
        "title": json.get("title") or "",
        "authors": json.get("authors") or "",
        "category": json.get("category") or "",
        "date": json.get("date") or "",
    }


def parse_rss(xml_text: str) -> list[dict[str, str]]:
    """Parse an RSS 2.0 or Atom feed into a list of entry dicts.

    Pure via ``xml.etree``. Returns entries with keys ``title``, ``link``,
    ``description``, ``date`` (atom feeds also ``id``).
    """
    entries: list[dict[str, str]] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return entries

    def _text(el, path, ns=""):
        node = el.find(path, {"a": ns} if ns else {})
        return (node.text or "").strip() if node is not None and node.text else ""

    # RSS 2.0
    for item in root.findall(".//item"):
        entries.append(
            {
                "title": _text(item, "title"),
                "link": _text(item, "link"),
                "description": _text(item, "description"),
                "date": _text(item, "pubDate"),
            }
        )
    if entries:
        return entries

    # Atom
    atom = "http://www.w3.org/2005/Atom"
    feed_entries = root.findall(f".//{{{atom}}}entry")
    if not feed_entries:
        feed_entries = root.findall(".//entry")
    for entry in feed_entries:
        link = ""
        links = entry.findall(f"{{{atom}}}link")
        if not links:
            links = entry.findall("link")
        for lnk in links:
            if lnk.get("href"):
                link = lnk.get("href", "")
                break

        def atext(tag):
            node = entry.find(f"{{{atom}}}{tag}")
            if node is None:
                node = entry.find(tag)
            return (node.text or "").strip() if node is not None and node.text else ""

        entries.append(
            {
                "title": atext("title"),
                "link": link,
                "description": atext("summary") or atext("content"),
                "date": atext("published") or atext("updated"),
                "id": atext("id"),
            }
        )
    return entries
