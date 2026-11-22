"""Real RDKit-based cheminformatics skills.

Implements actual molecular descriptor calculation, fingerprinting, and
SMILES validation using RDKit. Replaces the echo-stub behaviour of
`AgentOrchestrator.execute_skill` with working chemistry.
"""

from __future__ import annotations

from typing import Any

from rdkit import Chem, DataStructs
from rdkit.Chem import (
    QED,
    AllChem,
    Crippen,
    Descriptors,
    Lipinski,
    rdMolDescriptors,
)


def calculate_descriptors(smiles: str) -> dict[str, Any]:
    """Calculate standard molecular descriptors for a SMILES string.

    Returns MW, logP, HBD, HBA, TPSA, rotatable bonds, ring counts,
    aromatic fraction, formal charge, fraction Csp3, and QED.
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")

    return {
        "smiles": smiles,
        "canonical_smiles": Chem.MolToSmiles(mol),
        "inchi_key": Chem.MolToInchiKey(mol),
        "mw": round(Descriptors.MolWt(mol), 3),
        "exact_mw": round(Descriptors.ExactMolWt(mol), 4),
        "logp": round(Crippen.MolLogP(mol), 3),
        "mr": round(Crippen.MolMR(mol), 3),
        "hbd": Lipinski.NumHDonors(mol),
        "hba": Lipinski.NumHAcceptors(mol),
        "tpsa": round(rdMolDescriptors.CalcTPSA(mol), 3),
        "rotatable_bonds": Lipinski.NumRotatableBonds(mol),
        "aromatic_rings": Lipinski.NumAromaticRings(mol),
        "aliphatic_rings": Lipinski.NumAliphaticRings(mol),
        "ring_count": Lipinski.RingCount(mol),
        "fraction_csp3": round(Lipinski.FractionCSP3(mol), 3),
        "heavy_atom_count": Lipinski.HeavyAtomCount(mol),
        "formal_charge": sum(a.GetFormalCharge() for a in mol.GetAtoms()),
        "qed": round(QED.qed(mol), 3),
        "lipinski_violations": _lipinski_violations(mol),
    }


def _lipinski_violations(mol) -> int:
    """Number of Lipinski Rule-of-5 violations."""
    v = 0
    if Descriptors.MolWt(mol) > 500:
        v += 1
    if Crippen.MolLogP(mol) > 5:
        v += 1
    if Lipinski.NumHDonors(mol) > 5:
        v += 1
    if Lipinski.NumHAcceptors(mol) > 10:
        v += 1
    return v


def validate_smiles(smiles: str) -> dict[str, Any]:
    """Validate a SMILES string and return parse status plus any warnings."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"smiles": smiles, "valid": False, "error": "parse failure"}
    return {
        "smiles": smiles,
        "valid": True,
        "canonical_smiles": Chem.MolToSmiles(mol),
        "num_atoms": mol.GetNumAtoms(),
        "num_bonds": mol.GetNumBonds(),
    }


def calculate_fingerprint(smiles: str, radius: int = 2, n_bits: int = 2048) -> dict[str, Any]:
    """Compute a Morgan (ECFP-like) fingerprint bit vector."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")
    fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)
    return {
        "smiles": smiles,
        "radius": radius,
        "n_bits": n_bits,
        "bits": list(fp.GetOnBits()),
    }


def batch_fingerprints(
    smiles_list: list[str], radius: int = 2, n_bits: int = 2048
) -> tuple[list[str], Any]:
    """Compute a stacked bit matrix for a list of SMILES (valid-only)."""
    import numpy as np

    valid_smiles, fps = [], []
    for smi in smiles_list:
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            continue
        fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)
        arr = np.zeros((n_bits,), dtype=np.int8)
        DataStructs.ConvertToNumpyArray(fp, arr)
        valid_smiles.append(smi)
        fps.append(arr)
    if not fps:
        raise ValueError("No valid SMILES in input")
    return valid_smiles, np.vstack(fps)


def tanimoto(smiles_a: str, smiles_b: str, radius: int = 2, n_bits: int = 2048) -> float:
    """Tanimoto similarity between two molecules."""
    mol_a = Chem.MolFromSmiles(smiles_a)
    mol_b = Chem.MolFromSmiles(smiles_b)
    if mol_a is None or mol_b is None:
        raise ValueError("Invalid SMILES")
    fp_a = AllChem.GetMorganFingerprintAsBitVect(mol_a, radius, nBits=n_bits)
    fp_b = AllChem.GetMorganFingerprintAsBitVect(mol_b, radius, nBits=n_bits)
    return float(DataStructs.TanimotoSimilarity(fp_a, fp_b))


def run(operation: str, **kwargs) -> Any:
    """Dispatch operations for the orchestrator skill bridge."""
    ops = {
        "descriptors": calculate_descriptors,
        "validate": validate_smiles,
        "fingerprint": calculate_fingerprint,
        "tanimoto": tanimoto,
    }
    if operation not in ops:
        raise ValueError(f"Unknown operation '{operation}'; available: {sorted(ops)}")
    return ops[operation](**kwargs)
