"""semantic_scholar_api skill: paper/citation lookups via the S2 Graph API."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap

BASE_URL = "https://api.semanticscholar.org/graph/v1"
USER_AGENT = "openscience/0.1 (mailto:openscience@example.org)"
_TIMEOUT = 30


def _get_json(url: str) -> dict[str, Any]:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=_TIMEOUT) as resp:  # noqa: S310 - public API
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"S2 API error {exc.code} for {url}: {exc.reason}") from exc
    except (URLError, OSError) as exc:
        raise RuntimeError(f"S2 API request failed for {url}: {exc}") from exc


def parse_paper(json_obj: dict[str, Any]) -> dict[str, Any]:
    """Parse an S2 paper object into a flat dict (pure)."""
    authors = [a.get("name") or "" for a in json_obj.get("authors") or []]
    return {
        "paper_id": json_obj.get("paperId") or "",
        "title": json_obj.get("title") or "",
        "year": json_obj.get("year"),
        "authors": [a for a in authors if a],
        "venue": json_obj.get("venue") or "",
        "citation_count": json_obj.get("citationCount", 0),
        "abstract": json_obj.get("abstract") or "",
        "external_ids": json_obj.get("externalIds") or {},
    }


def paper(**kwargs: Any) -> dict[str, Any]:
    """Fetch one paper by id (S2 id, DOI:, PMID:, CorpusId:) — network."""
    kw = unwrap(kwargs)
    paper_id = kw.get("paper_id") or kw.get("id") or ""
    fields = kw.get("fields") or "title,abstract,authors,year,venue,citationCount,externalIds"
    url = f"{BASE_URL}/paper/{quote(str(paper_id), safe='')}?{urlencode({'fields': fields})}"
    return result(paper=parse_paper(_get_json(url)))


def citations(**kwargs: Any) -> dict[str, Any]:
    """Fetch citing papers for a paper id (network)."""
    kw = unwrap(kwargs)
    paper_id = kw.get("paper_id") or kw.get("id") or ""
    fields = kw.get("fields") or "title,authors,year,citationCount"
    limit = int(kw.get("limit", 20))
    url = (
        f"{BASE_URL}/paper/{quote(str(paper_id), safe='')}/citations?"
        + urlencode({"fields": fields, "limit": limit})
    )
    data = _get_json(url)
    citing = [parse_paper(c.get("citingPaper") or {}) for c in data.get("data") or []]
    return result(citations=citing, count=len(citing))


def parse_only(**kwargs: Any) -> dict[str, Any]:
    """Parse a provided S2 paper JSON dict (pure, no network)."""
    kw = unwrap(kwargs)
    return result(paper=parse_paper(kw.get("paper") or kw.get("json") or {}))


_OPS = {"paper": paper, "citations": citations, "parse_only": parse_only}


def run(operation: str = "run", **kwargs: Any) -> dict[str, Any]:
    """Dispatch to an operation; ``run`` defaults to ``paper``."""
    op = _OPS.get(operation) or _OPS["paper"]
    if operation not in _OPS and operation != "run":
        raise ValueError(f"Unknown operation {operation!r}. Available: {sorted(_OPS)}")
    return op(**kwargs)


register_skill("semantic_scholar_api", run)
