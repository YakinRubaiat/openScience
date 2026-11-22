"""Crossref connector (https://api.crossref.org) using stdlib urllib only.

Network functions (``works``, ``get_work``) are thin wrappers; all parsing
(``parse_item``) is pure and testable offline.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://api.crossref.org/works"
USER_AGENT = "openscience/0.1 (mailto:openscience@example.org)"
_TIMEOUT = 30


def _get_json(url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """GET ``url`` and return decoded JSON; RuntimeError with context on failure."""
    qs = urlencode(params or {})
    full = f"{url}?{qs}" if qs else url
    req = Request(full, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=_TIMEOUT) as resp:  # noqa: S310 - public API
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"Crossref API error {exc.code} for {full}: {exc.reason}") from exc
    except (URLError, OSError) as exc:
        raise RuntimeError(f"Crossref API request failed for {full}: {exc}") from exc


def works(query: str, rows: int = 20) -> dict[str, Any]:
    """Search Crossref works. Returns raw JSON response."""
    return _get_json(BASE_URL, {"query": query, "rows": rows})


def get_work(doi: str) -> dict[str, Any]:
    """Fetch a single work record by DOI. Returns raw JSON response."""
    return _get_json(f"{BASE_URL}/{doi}")


def parse_item(json: dict[str, Any]) -> dict[str, Any]:
    """Parse one Crossref work item into a flat dict."""
    authors = []
    for a in json.get("author") or []:
        name = " ".join(p for p in [a.get("given") or "", a.get("family") or ""] if p).strip()
        if name:
            authors.append(name)

    year = None
    published = ""
    for date_key in ("published-print", "published-online", "issued", "published"):
        parts = ((json.get(date_key) or {}).get("date-parts") or [[]])[0]
        if parts:
            year = parts[0]
            published = "-".join(str(p).zfill(2) if i else str(p) for i, p in enumerate(parts))
            break

    container = ""
    containers = json.get("container-title") or []
    if containers:
        container = containers[0]

    titles = json.get("title") or []
    return {
        "doi": json.get("DOI") or "",
        "title": titles[0] if titles else "",
        "authors": authors,
        "year": year,
        "container": container,
        "published": published,
    }
