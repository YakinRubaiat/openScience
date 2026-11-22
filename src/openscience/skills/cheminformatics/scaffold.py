"""Murcko scaffold analysis skill.

Registers:
- ``scaffold_analysis``
"""

from __future__ import annotations

from collections import Counter
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


def murcko_scaffold(smiles: str, **kwargs: Any) -> dict[str, Any]:
    """Return the Bemis–Murcko scaffold SMILES for a molecule."""
    scaffold_mod = optional_import("rdkit.Chem.Scaffolds.MurckoScaffold", "rdkit")
    mol = _mol_from_smiles(smiles)
    scaffold_smiles = scaffold_mod.MurckoScaffoldSmiles(mol=mol, includeChirality=False)
    generic_smiles = ""
    try:
        generic = scaffold_mod.MakeScaffoldGeneric(mol)
        generic_smiles = optional_import("rdkit.Chem", "rdkit").MolToSmiles(generic)
    except Exception:
        generic_smiles = ""
    framework = ""
    try:
        fw = scaffold_mod.GetScaffoldForMol(mol)
        framework = optional_import("rdkit.Chem", "rdkit").MolToSmiles(fw)
    except Exception:
        framework = scaffold_smiles
    return result(
        smiles=smiles,
        scaffold_smiles=scaffold_smiles,
        generic_scaffold=generic_smiles,
        framework=framework,
    )


def scaffold_counts(
    smiles_list: list[str],
    include_empty: bool = False,
    **kwargs: Any,
) -> dict[str, Any]:
    """Count Murcko scaffold occurrences across a list of SMILES."""
    scaffold_mod = optional_import("rdkit.Chem.Scaffolds.MurckoScaffold", "rdkit")
    counts: Counter[str] = Counter()
    n_valid = 0
    n_invalid = 0
    for smi in smiles_list or []:
        try:
            mol = _mol_from_smiles(smi)
        except ValueError:
            n_invalid += 1
            continue
        n_valid += 1
        scaf = scaffold_mod.MurckoScaffoldSmiles(mol=mol)
        if scaf == "" and not include_empty:
            scaf = "<no-scaffold>"
        counts[scaf] += 1
    histogram = [
        {"scaffold": scaf, "count": cnt}
        for scaf, cnt in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    return result(
        n_total=len(smiles_list or []),
        n_valid=n_valid,
        n_invalid=n_invalid,
        n_unique_scaffolds=len(histogram),
        histogram=histogram,
    )


def scaffold_tree_level(
    smiles: str,
    level: int = 1,
    **kwargs: Any,
) -> dict[str, Any]:
    """Return the scaffold-tree node at a given trimming level.

    Falls back to the plain Murcko scaffold when the tree decomposition
    (introduced in RDKit 2020.03) is unavailable.
    """
    scaffold_mod = optional_import("rdkit.Chem.Scaffolds.MurckoScaffold", "rdkit")
    chem = optional_import("rdkit.Chem", "rdkit")
    mol = _mol_from_smiles(smiles)

    try:
        tree = scaffold_mod.ScaffoldTree(mol)
        nodes = list(tree)
        if not nodes:
            raise RuntimeError("empty scaffold tree")
        idx = max(0, min(int(level) - 1, len(nodes) - 1))
        target = nodes[idx]
        level_smiles = chem.MolToSmiles(target)
        levels = len(nodes)
    except Exception:
        level_smiles = scaffold_mod.MurckoScaffoldSmiles(mol=mol)
        levels = 1
    return result(
        smiles=smiles,
        requested_level=int(level),
        resolved_level=min(int(level), levels),
        scaffold_tree_size=levels,
        scaffold_smiles=level_smiles,
    )


run = skill_run(
    {
        "murcko_scaffold": murcko_scaffold,
        "scaffold_counts": scaffold_counts,
        "scaffold_tree_level": scaffold_tree_level,
    }
)

register_skill("scaffold_analysis", run)
