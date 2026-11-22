"""AlphaFold Protein Structure Database connector.

Fetches predicted structures (and confidence summaries) from the AlphaFold
Protein Structure Database hosted by EMBL-EBI. Network access uses
:mod:`urllib.request`; all network errors surface as :class:`RuntimeError`.

See: https://alphafold.ebi.ac.uk/
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any

from openscience.skills._common import optional_import

API_BASE = "https://alphafold.ebi.ac.uk/api/prediction"
FILES_BASE = "https://alphafold.ebi.ac.uk/files"
USER_AGENT = "openscience-alphafold-connector/0.1"


@dataclass
class AlphaFoldPrediction:
    """Summary of one AlphaFold prediction record for a UniProt accession."""

    uniprot_id: str
    gene: str = ""
    organism: str = ""
    sequence: str = ""
    sequence_length: int = 0
    model_version: str = ""
    pae_version: str = ""
    pdb_url: str = ""
    pae_url: str = ""
    global_metric: float | None = None  # mean pLDDT (0-100)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _http_get(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except (urllib.error.URLError, OSError) as exc:
        raise RuntimeError(f"AlphaFold request failed: {url}: {exc}") from exc


def list_predictions(uniprot_id: str) -> list[AlphaFoldPrediction]:
    """Query the AlphaFold DB API for predictions of a UniProt accession.

    Returns one :class:`AlphaFoldPrediction` per available model (typically
    exactly one for the canonical sequence).
    """
    acc = uniprot_id.strip().upper()
    if not acc:
        raise ValueError("Empty UniProt accession")
    url = f"{API_BASE}/{urllib.parse.quote(acc)}"
    raw = _http_get(url)
    try:
        payload = json.loads(raw.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"AlphaFold API returned invalid JSON for {acc}: {exc}") from exc
    out: list[AlphaFoldPrediction] = []
    for rec in payload:
        seq = rec.get("uniprotSequence") or rec.get("sequence") or ""
        out.append(
            AlphaFoldPrediction(
                uniprot_id=rec.get("uniprotAccession", acc),
                gene=rec.get("gene", "") or "",
                organism=(
                    rec.get("organism") or rec.get("organismScientificNames", [""])[0] or ""
                ),
                sequence=seq,
                sequence_length=int(rec.get("sequenceLength") or len(seq) or 0),
                model_version=str(rec.get("latestVersion") or rec.get("modelVersion") or ""),
                pae_version=str(rec.get("latestPaeVersion") or rec.get("paeVersion") or ""),
                pdb_url=rec.get("pdbUrl", "") or "",
                pae_url=rec.get("paeUrl") or rec.get("paeDocUrl", "") or "",
                global_metric=_extract_global_metric(rec),
            )
        )
    return out


def _extract_global_metric(rec: dict[str, Any]) -> float | None:
    for key in ("globalMetricValue", "globalMetricPlddt", "plddt"):
        val = rec.get(key)
        if isinstance(val, (int, float)):
            return float(val)
    return None


def fetch_plddt_per_residue(prediction: AlphaFoldPrediction) -> list[float]:
    """Download the model's JSON and return per-residue pLDDT scores.

    Uses ``prediction.pae_url`` backing JSON from the DB. Raises
    :class:`RuntimeError` when no confidence JSON is available.
    """
    acc = prediction.uniprot_id
    if prediction.pdb_url.startswith(FILES_BASE):
        # Replace the structure file suffix with the predicted_aligned_error? No —
        # use the dedicated *ifle* URL naming scheme from the DB.
        base = prediction.pdb_url[:-4] if prediction.pdb_url.endswith(".pdb") else prediction.pdb_url
        conf_url = f"{base}-confidence_v{prediction.model_version or '4'}.json"
    else:
        model = prediction.model_version or "4"
        conf_url = f"{FILES_BASE}/AF-{acc}-F1-confidence_v{model}.json"
    raw = _http_get(conf_url)
    try:
        payload = json.loads(raw.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid confidence JSON from {conf_url}: {exc}") from exc
    scores = payload.get("confidenceScore")
    if not isinstance(scores, list):
        raise RuntimeError(f"Confidence JSON missing 'confidenceScore' list: {conf_url}")
    return [float(s) for s in scores]


class AlphaFoldConnector:
    """Minimal connector for the AlphaFold Protein Structure Database."""

    def search(self, uniprot_id: str) -> list[AlphaFoldPrediction]:
        """List models for a UniProt accession."""
        return list_predictions(uniprot_id)

    def fetch_pdb_text(self, prediction: AlphaFoldPrediction) -> str:
        """Download the predicted coordinate file (PDB text)."""
        if not prediction.pdb_url:
            raise RuntimeError(
                f"No pdb_url provided for {prediction.uniprot_id}; "
                "call `search()` first."
            )
        return _http_get(prediction.pdb_url).decode("utf-8", errors="replace")

    def mean_plddt(self, prediction: AlphaFoldPrediction) -> float:
        """Mean per-residue pLDDT across the whole model."""
        scores = fetch_plddt_per_residue(prediction)
        if not scores:
            raise RuntimeError(f"Empty per-residue confidence for {prediction.uniprot_id}")
        return sum(scores) / len(scores)

    def get_structure(self, prediction: AlphaFoldPrediction):
        """Parse a prediction into a Biopython ``Structure``.

        Requires the optional ``biopython`` dependency. Raises
        :class:`RuntimeError` when Biopython is missing.
        """
        import io

        pdb_mod = optional_import("Bio.PDB", "biopython")
        text = self.fetch_pdb_text(prediction)
        parser = pdb_mod.PDBParser(QUIET=True)
        return parser.get_structure(prediction.uniprot_id, io.StringIO(text))
