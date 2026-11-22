"""patent_api skill: Google Patents search (best-effort) and parse-only."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap

USER_AGENT = "openscience/0.1 (mailto:openscience@example.org)"
_TIMEOUT = 30


def search(**kwargs: Any) -> dict[str, Any]:
    """Search Google Patents via its public JSON suggestions endpoint (network).

    Best-effort: the endpoint is unofficial. Raises RuntimeError offline.
    """
    kw = unwrap(kwargs)
    query = kw.get("query") or ""
    url = "https://patents.google.com/xhr/query?" + urlencode(
        {"url": f"q%3D{query}", "exp": ""}
    )
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=_TIMEOUT) as resp:  # noqa: S310 - public API
            data = json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"Patents API error {exc.code} for {url}: {exc.reason}") from exc
    except (URLError, OSError) as exc:
        raise RuntimeError(f"Patents API request failed for {url}: {exc}") from exc
    return result(raw=data)


def get_patent(**kwargs: Any) -> dict[str, Any]:
    """Fetch a patent page (network) and return raw HTML text."""
    kw = unwrap(kwargs)
    patent_id = kw.get("patent_id") or ""
    url = f"https://patents.google.com/patent/{patent_id}/en"
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=_TIMEOUT) as resp:  # noqa: S310 - public API
            return result(patent_id=patent_id, html=resp.read().decode("utf-8", "replace"))
    except HTTPError as exc:
        raise RuntimeError(f"Patents API error {exc.code} for {url}: {exc.reason}") from exc
    except (URLError, OSError) as exc:
        raise RuntimeError(f"Patents API request failed for {url}: {exc}") from exc


def parse_only(**kwargs: Any) -> dict[str, Any]:
    """Parse a provided patent JSON dict into flat fields (pure, no network)."""
    patent = unwrap(kwargs).get("patent") or unwrap(kwargs).get("json") or {}
    return result(
        patent={
            "patent_id": patent.get("publication_number") or patent.get("id") or "",
            "title": patent.get("title") or "",
            "assignee": patent.get("assignee") or "",
            "inventors": patent.get("inventors") or [],
            "filing_date": patent.get("filing_date") or "",
            "abstract": patent.get("abstract") or "",
        }
    )


_OPS = {"search": search, "get_patent": get_patent, "parse_only": parse_only}


def run(operation: str = "run", **kwargs: Any) -> dict[str, Any]:
    """Dispatch to an operation; ``run`` defaults to ``parse_only``."""
    op = _OPS.get(operation) or _OPS["parse_only"]
    if operation not in _OPS and operation != "run":
        raise ValueError(f"Unknown operation {operation!r}. Available: {sorted(_OPS)}")
    return op(**kwargs)


register_skill("patent_api", run)
