"""biorxiv_api skill: fetch bioRxiv/medRxiv detail records and parse fixtures."""

from __future__ import annotations

from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap


def fetch_details(**kwargs: Any) -> dict[str, Any]:
    """Fetch preprint details in a date range (network)."""
    kw = unwrap(kwargs)
    from openscience.connectors.papers import biorxiv

    resp = biorxiv.fetch_details(
        server=kw.get("server") or "biorxiv",
        date_from=kw.get("date_from") or kw.get("from") or "",
        date_to=kw.get("date_to") or kw.get("to") or "",
        cursor=int(kw.get("cursor", 0)),
    )
    records = [biorxiv.parse_record(r) for r in resp.get("collection") or []]
    return result(records=records, count=len(records))


def parse_only(**kwargs: Any) -> dict[str, Any]:
    """Parse provided record(s) (pure, no network)."""
    kw = unwrap(kwargs)
    from openscience.connectors.papers import biorxiv

    if isinstance(kw.get("records"), list):
        records = [biorxiv.parse_record(r) for r in kw["records"]]
        return result(records=records, count=len(records))
    record = kw.get("record") or kw.get("json") or {}
    return result(record=biorxiv.parse_record(record))


_OPS = {"fetch_details": fetch_details, "parse_only": parse_only}


def run(operation: str = "run", **kwargs: Any) -> dict[str, Any]:
    """Dispatch to an operation; ``run`` defaults to ``fetch_details``."""
    op = _OPS.get(operation) or _OPS["fetch_details"]
    if operation not in _OPS and operation != "run":
        raise ValueError(f"Unknown operation {operation!r}. Available: {sorted(_OPS)}")
    return op(**kwargs)


register_skill("biorxiv_api", run)
