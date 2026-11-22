"""ZINC database connector (purchasable compounds).

Uses the public ZINC15 API for substance lookup. Network access uses
:mod:`urllib.request`; network errors surface as :class:`RuntimeError`.

See: https://zinc15.docking.org/
"""

from __future__ import annotations

import csv
import io
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any

API_BASE = "https://zinc15.docking.org"
USER_AGENT = "openscience-zinc-connector/0.1"


@dataclass
class ZincSubstance:
    """A ZINC substance record."""

    zinc_id: str
    smiles: str = ""
    mw: float | None = None
    logp: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ZincSearchPage:
    """One page of ZINC search results."""

    items: list[ZincSubstance]
    count: int
    next_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [s.to_dict() for s in self.items],
            "count": self.count,
            "next_url": self.next_url,
        }


def _http_get(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise RuntimeError(f"ZINC record not found: {url}") from exc
        raise RuntimeError(f"ZINC API error {exc.code}: {url}") from exc
    except (urllib.error.URLError, OSError) as exc:
        raise RuntimeError(f"ZINC request failed: {url}: {exc}") from exc


def _parse_tsv(text: str) -> list[ZincSubstance]:
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    out: list[ZincSubstance] = []
    for row in reader:
        smiles = row.get("smiles") or row.get("smile") or ""
        zinc_id = row.get("zinc_id") or row.get("zincid") or ""
        if not (zinc_id or smiles):
            continue
        out.append(
            ZincSubstance(
                zinc_id=zinc_id,
                smiles=smiles,
                mw=_safe_float(row.get("mwt")),
                logp=_safe_float(row.get("logp")),
            )
        )
    return out


def _safe_float(val: Any) -> float | None:
    try:
        if val in (None, ""):
            return None
        return float(val)
    except (TypeError, ValueError):
        return None


class ZincConnector:
    """Minimal connector for ZINC15.

    Supports fetching a single substance by ZINC ID and a basic SMILES-based
    search via ``/substances/smiles-<smiles>.txt``.
    """

    def get_substance(self, zinc_id: str) -> ZincSubstance:
        """Fetch a single substance by ZINC ID such as ``ZINC000000000053``."""
        zinc_id_clean = zinc_id.strip()
        if not zinc_id_clean:
            raise ValueError("Empty ZINC ID")
        url = f"{API_BASE}/substances/{urllib.parse.quote(zinc_id_clean)}.txt"
        text = _http_get(url).decode("utf-8", errors="replace")
        items = _parse_tsv(text)
        if not items:
            raise RuntimeError(f"ZINC substance {zinc_id_clean} not found")
        return items[0]

    def search_by_smiles(self, smiles: str, max_items: int = 25) -> ZincSearchPage:
        """Exact/near search by SMILES string."""
        smiles_clean = smiles.strip()
        if not smiles_clean:
            raise ValueError("Empty SMILES")
        url = (
            f"{API_BASE}/substances/smiles-"
            f"{urllib.parse.quote(smiles_clean, safe='')}.txt"
            f"?count={int(max_items)}"
        )
        text = _http_get(url).decode("utf-8", errors="replace")
        items = _parse_tsv(text)[: int(max_items)]
        return ZincSearchPage(items=items, count=len(items))

    def substance_info(self, zinc_id: str) -> dict[str, Any]:
        """Return the substance record plus description from the JSON-ish page.

        ZINC15 does not expose a stable JSON API for single substances across
        all releases, so this endpoint falls back to the TSV parser and reuses
        :meth:`get_substance`.
        """
        return self.get_substance(zinc_id).to_dict()
