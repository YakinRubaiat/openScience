"""RCSB Protein Data Bank connector.

Downloads PDB/mmCIF coordinate files from the RCSB PDB archive via the
public download endpoint. Network access uses :mod:`urllib.request` so the
connector works without the optional ``requests`` dependency; all network
errors surface as :class:`RuntimeError` with a clear message.

See: https://www.rcsb.org/ and https://files.rcsb.org/
"""

from __future__ import annotations

import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any

from openscience.skills._common import optional_import

RCSB_DOWNLOAD_BASE = "https://files.rcsb.org/download"
USER_AGENT = "openscience-pdb-connector/0.1"


@dataclass
class ChainInfo:
    """Summary of a single chain in a PDB structure."""

    chain_id: str
    residue_count: int
    has_hetatm: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PDBRecord:
    """Parsed header + chain summary for a PDB entry."""

    pdb_id: str
    title: str = ""
    chains: list[ChainInfo] = field(default_factory=list)
    resolution: float | None = None
    deposition_date: str = ""
    classification: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["pdb_id"] = self.pdb_id.upper()
        return d


def fetch_pdb_text(pdb_id: str, file_format: str = "pdb") -> str:
    """Download raw PDB/mmCIF text from RCSB.

    Args:
        pdb_id: 4-character PDB identifier (case-insensitive).
        file_format: ``"pdb"`` or ``"cif"``.

    Raises:
        RuntimeError: on any network/HTTP error.
    """
    pdb_id_clean = pdb_id.strip().upper()
    if len(pdb_id_clean) != 4:
        raise ValueError(f"Invalid PDB ID {pdb_id!r}: must be 4 characters")
    ext = {"pdb": ".pdb", "cif": ".cif"}.get(file_format.lower())
    if ext is None:
        raise ValueError(f"Unsupported file_format {file_format!r}; use 'pdb' or 'cif'")
    url = f"{RCSB_DOWNLOAD_BASE}/{pdb_id_clean}{ext}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError) as exc:
        raise RuntimeError(f"RCSB PDB download failed for {pdb_id_clean}: {exc}") from exc


def parse_pdb_text(text: str, pdb_id: str = "") -> PDBRecord:
    """Parse TITLE/COMPND/REMARK 2 chains from raw PDB-format text.

    Pure-python parsing: counts ATOM records per chain on the fly. For heavy
    structural analysis, prefer :class:`PDBConnector.get_structure`.
    """
    title_parts: list[str] = []
    classification_parts: list[str] = []
    resolution: float | None = None
    deposition_date = ""
    chains: dict[str, bool] = {}

    for line in text.splitlines():
        record = line[0:6].strip()
        if record == "HEADER":
            classification_parts.append(line[10:50].strip())
            deposition_date = line[50:59].strip()
        elif record == "TITLE":
            title_parts.append(line[10:80].rstrip())
        elif record == "REMARK" and line[7:10].strip() == "2":
            # REMARK 2 RESOLUTION line
            if "RESOLUTION." in line:
                try:
                    # "REMARK   2 RESOLUTION.  1.50 ANGSTROMS." -> 1.50
                    tokens = line.split()
                    res_idx = tokens.index("RESOLUTION.")
                    resolution = float(tokens[res_idx + 1])
                except (ValueError, IndexError):
                    pass
        elif record in ("ATOM", "HETATM"):
            chain_id = line[21:22].strip() or "_"
            chains.setdefault(chain_id, False)
            if record == "HETATM":
                chains[chain_id] = True

    chain_infos = []
    residue_counts: dict[str, int] = {}
    # Count unique residues per chain (by residue-number + insertion code).
    seen_residues: set[tuple[str, str, str]] = set()
    for line in text.splitlines():
        if line[0:6].strip() == "ATOM":
            chain_id = line[21:22].strip() or "_"
            res_key = (chain_id, line[22:26].strip(), line[26:27].strip())
            if res_key in seen_residues:
                continue
            seen_residues.add(res_key)
            residue_counts[chain_id] = residue_counts.get(chain_id, 0) + 1
    for chain_id, has_het in chains.items():
        chain_infos.append(
            ChainInfo(
                chain_id=chain_id,
                residue_count=residue_counts.get(chain_id, 0),
                has_hetatm=has_het,
            )
        )

    return PDBRecord(
        pdb_id=pdb_id,
        title=" ".join(title_parts).strip(),
        chains=chain_infos,
        resolution=resolution,
        deposition_date=deposition_date,
        classification=" ".join(classification_parts).strip(),
    )


class PDBConnector:
    """Minimal connector for the RCSB PDB archive.

    Includes an optional Biopython-backed structural interface that is
    enabled only when Biopython is installed (``openscience[bio]``).
    """

    def fetch_text(self, pdb_id: str, file_format: str = "pdb") -> str:
        """Download raw coordinate text."""
        return fetch_pdb_text(pdb_id, file_format=file_format)

    def fetch_record(self, pdb_id: str) -> PDBRecord:
        """Download and parse header/chain summary."""
        return parse_pdb_text(self.fetch_text(pdb_id), pdb_id=pdb_id.strip().upper())

    def get_structure(self, pdb_id: str, file_format: str = "pdb"):
        """Parse the entry into a Biopython ``Structure`` object.

        Requires the optional ``biopython`` dependency. Raises
        :class:`RuntimeError` when Biopython is missing.
        """
        text = self.fetch_text(pdb_id, file_format=file_format)
        if file_format.lower() == "cif":
            return self._parse_cif(text, pdb_id)
        return self._parse_pdb(text, pdb_id)

    def _parse_pdb(self, text: str, pdb_id: str):
        import io

        pdb_mod = optional_import("Bio.PDB", "biopython")
        parser = pdb_mod.PDBParser(QUIET=True)
        return parser.get_structure(pdb_id.upper(), io.StringIO(text))

    def _parse_cif(self, text: str, pdb_id: str):
        import io

        pdb_mod = optional_import("Bio.PDB", "biopython")
        parser = pdb_mod.MMCIFParser(QUIET=True)
        return parser.get_structure(pdb_id.upper(), io.StringIO(text))
