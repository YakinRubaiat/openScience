"""ChEMBL database connector (small-molecule bioactivity).

Uses the public ChEMBL REST API. Network access uses :mod:`urllib.request`;
network errors surface as :class:`RuntimeError`.

See: https://www.ebi.ac.uk/chembl/api/data/docs
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any

API_BASE = "https://www.ebi.ac.uk/chembl/api/data"
USER_AGENT = "openscience-chembl-connector/0.1"


@dataclass
class ChemblMolecule:
    """A ChEMBL compound record."""

    chembl_id: str
    pref_name: str = ""
    molecule_type: str = ""
    max_phase: float | None = None
    canonical_smiles: str = ""
    inchi_key: str = ""
    mw_freebase: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ChemblActivity:
    """A bioactivity measurement."""

    molecule_chembl_id: str
    target_chembl_id: str
    standard_type: str = ""
    standard_relation: str = ""
    standard_value: float | None = None
    standard_units: str = ""
    pchembl_value: float | None = None
    assay_description: str = ""
    document_chembl_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ChemblTarget:
    """A ChEMBL target record."""

    target_chembl_id: str
    pref_name: str = ""
    target_type: str = ""
    organism: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _get_json(path: str, params: dict[str, Any] | None = None, timeout: int = 30) -> dict[str, Any]:
    qs = ""
    if params:
        qs = "?" + urllib.parse.urlencode(params)
    url = f"{API_BASE}/{path.lstrip('/')}.json{qs}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise RuntimeError(f"ChEMBL record not found: {url}") from exc
        raise RuntimeError(f"ChEMBL API error {exc.code}: {url}") from exc
    except (urllib.error.URLError, OSError) as exc:
        raise RuntimeError(f"ChEMBL request failed: {url}: {exc}") from exc


def _molecule_from_record(rec: dict[str, Any]) -> ChemblMolecule:
    structures = rec.get("molecule_structures") or {}
    return ChemblMolecule(
        chembl_id=rec.get("molecule_chembl_id", ""),
        pref_name=rec.get("pref_name") or "",
        molecule_type=rec.get("molecule_type") or "",
        max_phase=_safe_float(rec.get("max_phase")),
        canonical_smiles=structures.get("canonical_smiles") or "",
        inchi_key=structures.get("standard_inchi_key") or "",
        mw_freebase=_safe_float(rec.get("molecule_properties", {}).get("mw_freebase"))
        if rec.get("molecule_properties")
        else None,
    )


def _safe_float(val: Any) -> float | None:
    try:
        if val in (None, ""):
            return None
        return float(val)
    except (TypeError, ValueError):
        return None


class ChemblConnector:
    """Minimal connector for the ChEMBL REST API."""

    def search_molecules(
        self, query: str, limit: int = 10
    ) -> list[ChemblMolecule]:
        """Free-text search of the ``/molecule/search`` endpoint."""
        if not query or not query.strip():
            raise ValueError("Empty search query")
        data = _get_json("molecule/search", {"q": query.strip(), "limit": int(limit)})
        molecules = data.get("molecules") or []
        return [_molecule_from_record(rec) for rec in molecules]

    def get_molecule(self, chembl_id: str) -> ChemblMolecule:
        """Fetch a single molecule by ChEMBL ID (e.g. ``CHEMBL25``)."""
        data = _get_json(f"molecule/{urllib.parse.quote(chembl_id)}")
        if not isinstance(data, dict) or not data.get("molecule_chembl_id"):
            raise RuntimeError(f"ChEMBL molecule {chembl_id} not found")
        return _molecule_from_record(data)

    def get_activities(
        self,
        target_chembl_id: str | None = None,
        molecule_chembl_id: str | None = None,
        standard_type: str | None = None,
        limit: int = 20,
    ) -> list[ChemblActivity]:
        """Query ``/activity`` by target and/or molecule ChEMBL ID."""
        params: dict[str, Any] = {"limit": int(limit)}
        if target_chembl_id:
            params["target_chembl_id"] = target_chembl_id
        if molecule_chembl_id:
            params["molecule_chembl_id"] = molecule_chembl_id
        if standard_type:
            params["standard_type"] = standard_type
        data = _get_json("activity", params)
        activities = data.get("activities") or []
        return [
            ChemblActivity(
                molecule_chembl_id=rec.get("molecule_chembl_id", ""),
                target_chembl_id=rec.get("target_chembl_id", ""),
                standard_type=rec.get("standard_type") or "",
                standard_relation=rec.get("standard_relation") or "",
                standard_value=_safe_float(rec.get("standard_value")),
                standard_units=rec.get("standard_units") or "",
                pchembl_value=_safe_float(rec.get("pchembl_value")),
                assay_description=rec.get("assay_description") or "",
                document_chembl_id=rec.get("document_chembl_id") or "",
            )
            for rec in activities
        ]

    def search_targets(self, query: str, limit: int = 10) -> list[ChemblTarget]:
        """Free-text search of the ``/target`` endpoint."""
        if not query or not query.strip():
            raise ValueError("Empty search query")
        data = _get_json("target/search", {"q": query.strip(), "limit": int(limit)})
        targets = data.get("targets") or []
        return [
            ChemblTarget(
                target_chembl_id=rec.get("target_chembl_id", ""),
                pref_name=rec.get("pref_name") or "",
                target_type=rec.get("target_type") or "",
                organism=rec.get("organism") or "",
            )
            for rec in targets
        ]
