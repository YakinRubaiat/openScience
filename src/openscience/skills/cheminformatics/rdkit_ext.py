"""Extended RDKit descriptor skill.

Registers:
- ``rdkit_descriptors_ext``
"""

from __future__ import annotations

from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import optional_import, result, skill_run


def _mol_from_smiles(smiles: str):
    if not smiles or not smiles.strip():
        raise ValueError("Empty SMILES")
    chem = optional_import("rdkit.Chem", "rdkit")
    mol = chem.MolFromSmiles(smiles.strip())
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles!r}")
    return mol


def all_descriptors(smiles: str, **kwargs: Any) -> dict[str, Any]:
    """Compute every ``rdkit.Chem.rdMolDescriptors`` descriptor for a SMILES.

    Returns a flat ``{name: value}`` mapping. Values that fail to compute on
    unusual inputs (e.g. inorganic species) are omitted.
    """
    mol = _mol_from_smiles(smiles)
    descriptors_mod = optional_import("rdkit.Chem.rdMolDescriptors", "rdkit")
    chem = optional_import("rdkit.Chem", "rdkit")

    # Use the rdkit descriptor catalogue via ``rdkit.Chem.Descriptors`` which
    # exposes ``_descList`` of (name, fn).
    desc = optional_import("rdkit.Chem.Descriptors", "rdkit")
    desc_list = getattr(desc, "_descList", None) or []
    values: dict[str, Any] = {}
    for name, fn in desc_list:
        try:
            val = fn(mol)
        except Exception:
            continue
        if isinstance(val, (int, float)):
            values[name] = float(val) if isinstance(val, float) else int(val)
    values["canonical_smiles"] = chem.MolToSmiles(mol)
    values["inchi_key"] = chem.MolToInchiKey(mol)
    values["descriptor_count"] = len([v for v in values.values() if not isinstance(v, str)])
    _ = descriptors_mod  # kept rdkit module import for side-effect clarity
    return result(smiles=smiles, descriptors=values, count=values["descriptor_count"])


def lipinski_flags(smiles: str, **kwargs: Any) -> dict[str, Any]:
    """Return per-rule pass/fail for Lipinski's Rule of Five."""
    mol = _mol_from_smiles(smiles)
    desc = optional_import("rdkit.Chem.Descriptors", "rdkit")
    lip = optional_import("rdkit.Chem.Lipinski", "rdkit")
    crippen = optional_import("rdkit.Chem.Crippen", "rdkit")

    mw = desc.MolWt(mol)
    logp = crippen.MolLogP(mol)
    hbd = lip.NumHDonors(mol)
    hba = lip.NumHAcceptors(mol)
    flags = {
        "mw_ok": mw <= 500.0,
        "logp_ok": logp <= 5.0,
        "hbd_ok": hbd <= 5,
        "hba_ok": hba <= 10,
    }
    violations = [name for name, ok in flags.items() if not ok]
    return result(
        smiles=smiles,
        flags=flags,
        violations=violations,
        violation_count=len(violations),
        passes_ro5=len(violations) == 0,
        mw=round(mw, 3),
        logp=round(logp, 3),
        hbd=int(hbd),
        hba=int(hba),
    )


def rotatable_estimate(smiles: str, **kwargs: Any) -> dict[str, Any]:
    """Estimate rotatable-bond count plus a flexibility index."""
    mol = _mol_from_smiles(smiles)
    lip = optional_import("rdkit.Chem.Lipinski", "rdkit")
    rigid = optional_import("rdkit.Chem.rdMolDescriptors", "rdkit")

    rot = lip.NumRotatableBonds(mol)
    heavy = lip.HeavyAtomCount(mol)
    rings = lip.RingCount(mol)
    # Empirical flexibility: fraction of heavy atoms on rotatable side chains.
    # Formula below uses a 0-1 bounded heuristic.
    flex = (rot / max(heavy, 1)) ** 0.5 if heavy else 0.0
    return result(
        smiles=smiles,
        rotatable_bonds=int(rot),
        heavy_atoms=int(heavy),
        ring_count=int(rings),
        num_spiro_atoms=int(getattr(rigid, "CalcNumSpiroAtoms", lambda m: 0)(mol))
        if hasattr(rigid, "CalcNumSpiroAtoms")
        else 0,
        flexibility_index=round(flex, 3),
    )


run = skill_run(
    {
        "all_descriptors": all_descriptors,
        "lipinski_flags": lipinski_flags,
        "rotatable_estimate": rotatable_estimate,
    }
)

register_skill("rdkit_descriptors_ext", run)
