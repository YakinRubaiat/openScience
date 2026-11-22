"""Murcko scaffold analysis skill.

Registers:
- ``scaffold_analysis``

Uses ``rdkit.Chem.Scaffolds.MurckoScaffold``. Falls back to the pure-python
``_pyGetScaffoldForMol`` implementation when the C++ ``MurckoDecompose``
backend raises a ``RuntimeError`` (observed on some RDKit 2026 builds).
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


def _scaffold_mol(mol):
    """Return the Bemis–Murcko scaffold ``Mol``. Falls back to _pyGetScaffoldForMol."""
    scaffold_mod = optional_import("rdkit.Chem.Scaffolds.MurckoScaffold", "rdkit")
    try:
        return scaffold_mod.GetScaffoldForMol(mol)
    except RuntimeError:
        # Some RDKit builds (2026.x) ship a broken MurckoDecompose C++ binding;
        # the pure-python implementation below gives the identical result.
        return scaffold_mod._pyGetScaffoldForMol(mol)


def murcko_scaffold(smiles: str, **kwargs: Any) -> dict[str, Any]:
    """Return the Bemis–Murcko scaffold SMILES for a molecule."""
    scaffold_mod = optional_import("rdkit.Chem.Scaffolds.MurckoScaffold", "rdkit")
    chem = optional_import("rdkit.Chem", "rdkit")
    mol = _mol_from_smiles(smiles)
    scaffold = _scaffold_mol(mol)
    scaffold_smiles = chem.MolToSmiles(scaffold) if scaffold is not None else ""
    generic_smiles = ""
    try:
        generic = scaffold_mod.MakeScaffoldGeneric(mol)
        generic_smiles = chem.MolToSmiles(generic)
    except Exception:
        generic_smiles = ""
    return result(
        smiles=smiles,
        scaffold_smiles=scaffold_smiles,
        generic_scaffold=generic_smiles,
        framework=scaffold_smiles,
    )


def scaffold_counts(
    smiles_list: list[str],
    include_empty: bool = False,
    **kwargs: Any,
) -> dict[str, Any]:
    """Count Murcko scaffold occurrences across a list of SMILES."""
    chem = optional_import("rdkit.Chem", "rdkit")
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
        scaf_mol = _scaffold_mol(mol)
        scaf = chem.MolToSmiles(scaf_mol) if scaf_mol is not None else ""
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

    When ``MurckoScaffold.ScaffoldTree`` is unavailable (e.g. RDKit <2020.03
    or stripped builds), falls back to the plain Murcko scaffold with a
    tree size of 1.
    """
    scaffold_mod = optional_import("rdkit.Chem.Scaffolds.MurckoScaffold", "rdkit")
    chem = optional_import("rdkit.Chem", "rdkit")
    mol = _mol_from_smiles(smiles)

    tree_cls = getattr(scaffold_mod, "ScaffoldTree", None)
    level_smiles = ""
    levels = 1
    if tree_cls is not None:
        try:
            tree = tree_cls(mol)
            nodes = list(tree)
            if nodes:
                idx = max(0, min(int(level) - 1, len(nodes) - 1))
                level_smiles = chem.MolToSmiles(nodes[idx])
                levels = len(nodes)
        except Exception:
            tree_cls = None
    if not level_smiles:
        scaf_mol = _scaffold_mol(mol)
        level_smiles = chem.MolToSmiles(scaf_mol) if scaf_mol is not None else ""
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
