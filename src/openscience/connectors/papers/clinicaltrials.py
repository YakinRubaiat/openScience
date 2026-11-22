"""ClinicalTrials.gov API v2 connector using stdlib urllib only.

Network functions (``search``) are thin wrappers; all parsing
(``parse_study``) is pure and testable offline.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
USER_AGENT = "openscience/0.1 (mailto:openscience@example.org)"
_TIMEOUT = 30


def search(query: str, page_size: int = 10) -> dict[str, Any]:
    """Search ClinicalTrials.gov v2. Returns raw JSON response."""
    url = f"{BASE_URL}?{urlencode({'query.term': query, 'pageSize': page_size})}"
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=_TIMEOUT) as resp:  # noqa: S310 - public API
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(
            f"ClinicalTrials API error {exc.code} for {url}: {exc.reason}"
        ) from exc
    except (URLError, OSError) as exc:
        raise RuntimeError(f"ClinicalTrials API request failed for {url}: {exc}") from exc


def parse_study(json: dict[str, Any]) -> dict[str, Any]:
    """Parse one CT.gov v2 study object into a flat dict."""
    proto = json.get("protocolSection") or {}
    ident = proto.get("identificationModule") or {}
    status_mod = proto.get("statusModule") or {}
    design = proto.get("designModule") or {}
    cond_mod = proto.get("conditionsModule") or {}
    arms = proto.get("armsInterventionsModule") or {}

    phases = design.get("phases") or []
    interventions = [iv.get("name") or "" for iv in arms.get("interventions") or []]
    return {
        "nct_id": ident.get("nctId") or "",
        "title": ident.get("briefTitle") or ident.get("officialTitle") or "",
        "status": status_mod.get("overallStatus") or "",
        "phase": ", ".join(phases),
        "conditions": cond_mod.get("conditions") or [],
        "interventions": [i for i in interventions if i],
        "enrollment": (design.get("enrollmentInfo") or {}).get("count"),
    }
