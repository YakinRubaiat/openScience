"""OpenAlex connector (https://api.openalex.org) using stdlib urllib only.

Network functions (``search_works``) are thin wrappers; all parsing
(``parse_work``, ``reconstruct_abstract``) is pure and testable offline.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://api.openalex.org/works"
USER_AGENT = "openscience/0.1 (mailto:openscience@example.org)"
_TIMEOUT = 30


def _get_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    """GET ``url`` with query params and return decoded JSON.

    Raises RuntimeError with context on any network/HTTP failure.
    """
    qs = urlencode({k: v for k, v in params.items() if v is not None})
    full = f"{url}?{qs}" if qs else url
    req = Request(full, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=_TIMEOUT) as resp:  # noqa: S310 - public API
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"OpenAlex API error {exc.code} for {full}: {exc.reason}") from exc
    except (URLError, OSError) as exc:
        raise RuntimeError(f"OpenAlex API request failed for {full}: {exc}") from exc


def search_works(
    query: str, per_page: int = 25, filters: dict[str, str] | None = None
) -> dict[str, Any]:
    """Search OpenAlex works. Returns the raw JSON response.

    ``filters`` is a dict of OpenAlex filter terms, e.g.
    ``{"from_publication_date": "2020-01-01"}`` -> comma-joined ``filter`` param.
    """
    params: dict[str, Any] = {"search": query, "per-page": per_page}
    if filters:
        params["filter"] = ",".join(f"{k}:{v}" for k, v in filters.items())
    return _get_json(BASE_URL, params)


def reconstruct_abstract(inv_index: dict[str, list[int]] | None) -> str:
    """Rebuild an abstract string from OpenAlex's inverted word index.

    The index maps each word to the list of positions it appears at; the
    abstract is recovered by sorting words by their first position.
    """
    if not inv_index:
        return ""
    words: list[tuple[int, str]] = []
    for word, positions in inv_index.items():
        for pos in positions:
            words.append((pos, word))
    words.sort(key=lambda t: t[0])
    return " ".join(w for _, w in words)


def parse_work(json: dict[str, Any]) -> dict[str, Any]:
    """Parse one OpenAlex work object into a flat dict."""
    authors = [
        ((a.get("author") or {}).get("display_name") or "")
        for a in json.get("authorships") or []
    ]
    authors = [a for a in authors if a]
    source = ""
    primary = json.get("primary_location") or {}
    src = primary.get("source") or {}
    source = src.get("display_name") or ""
    return {
        "openalex_id": json.get("id") or "",
        "doi": (json.get("doi") or "").replace("https://doi.org/", ""),
        "title": json.get("title") or "",
        "year": json.get("publication_year"),
        "authors": authors,
        "cited_by_count": json.get("cited_by_count", 0),
        "source": source,
        "abstract": reconstruct_abstract(json.get("abstract_inverted_index")),
    }
