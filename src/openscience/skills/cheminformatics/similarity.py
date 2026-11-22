"""Molecular similarity skill.

Registers:
- ``molecular_similarity``
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


def _fingerprint(mol, radius: int = 2, n_bits: int = 2048):
    fpgen = optional_import("rdkit.Chem.rdFingerprintGenerator", "rdkit")
    gen = fpgen.GetMorganGenerator(radius=int(radius), fpSize=int(n_bits))
    return gen.GetFingerprint(mol)


def tanimoto(
    smiles_a: str,
    smiles_b: str,
    radius: int = 2,
    n_bits: int = 2048,
    **kwargs: Any,
) -> dict[str, Any]:
    """Tanimoto similarity between two SMILES using Morgan fingerprints."""
    ds = optional_import("rdkit.DataStructs", "rdkit")
    mol_a = _mol_from_smiles(smiles_a)
    mol_b = _mol_from_smiles(smiles_b)
    fp_a = _fingerprint(mol_a, radius, n_bits)
    fp_b = _fingerprint(mol_b, radius, n_bits)
    score = float(ds.TanimotoSimilarity(fp_a, fp_b))
    return result(
        smiles_a=smiles_a,
        smiles_b=smiles_b,
        radius=int(radius),
        n_bits=int(n_bits),
        tanimoto=round(score, 4),
    )


def dice(
    smiles_a: str,
    smiles_b: str,
    radius: int = 2,
    n_bits: int = 2048,
    **kwargs: Any,
) -> dict[str, Any]:
    """Dice similarity between two SMILES using Morgan fingerprints."""
    ds = optional_import("rdkit.DataStructs", "rdkit")
    mol_a = _mol_from_smiles(smiles_a)
    mol_b = _mol_from_smiles(smiles_b)
    fp_a = _fingerprint(mol_a, radius, n_bits)
    fp_b = _fingerprint(mol_b, radius, n_bits)
    score = float(ds.DiceSimilarity(fp_a, fp_b))
    return result(
        smiles_a=smiles_a,
        smiles_b=smiles_b,
        radius=int(radius),
        n_bits=int(n_bits),
        dice=round(score, 4),
    )


def most_similar(
    query_smiles: str,
    smiles_list: list[str],
    top_k: int = 5,
    radius: int = 2,
    n_bits: int = 2048,
    metric: str = "tanimoto",
    **kwargs: Any,
) -> dict[str, Any]:
    """Rank ``smiles_list`` by similarity to ``query_smiles``.

    Invalid entries in ``smiles_list`` are skipped. Returns up to ``top_k``
    hits sorted by descending score.
    """
    ds = optional_import("rdkit.DataStructs", "rdkit")
    query_mol = _mol_from_smiles(query_smiles)
    fp_q = _fingerprint(query_mol, radius, n_bits)
    if metric == "tanimoto":
        score_fn = ds.TanimotoSimilarity
    elif metric == "dice":
        score_fn = ds.DiceSimilarity
    else:
        raise ValueError(f"Unknown metric {metric!r}; expected 'tanimoto' or 'dice'")

    hits: list[dict[str, Any]] = []
    for smi in smiles_list or []:
        try:
            mol = _mol_from_smiles(smi)
        except ValueError:
            continue
        fp = _fingerprint(mol, radius, n_bits)
        score = float(score_fn(fp_q, fp))
        hits.append({"smiles": smi, "score": round(score, 4)})
    hits.sort(key=lambda h: h["score"], reverse=True)
    return result(
        query_smiles=query_smiles,
        metric=metric,
        radius=int(radius),
        n_bits=int(n_bits),
        top_k=int(top_k),
        hits=hits[: int(top_k)],
        n_evaluated=len(hits),
    )


def cluster_butina(
    smiles_list: list[str],
    threshold: float = 0.7,
    radius: int = 2,
    n_bits: int = 2048,
    **kwargs: Any,
) -> dict[str, Any]:
    """Cluster SMILES with the Butina algorithm using Tanimoto distance."""
    ds = optional_import("rdkit.DataStructs", "rdkit")
    cluster_mod = optional_import("rdkit.ML.Cluster.Butina", "rdkit")
    mols = []
    valid_smiles = []
    for smi in smiles_list or []:
        try:
            mol = _mol_from_smiles(smi)
        except ValueError:
            continue
        mols.append(mol)
        valid_smiles.append(smi)
    if not mols:
        raise ValueError("No valid SMILES in input")
    fps = [_fingerprint(m, radius, n_bits) for m in mols]
    dists = []
    nfps = len(fps)
    for i in range(1, nfps):
        sims = ds.BulkTanimotoSimilarity(fps[i], fps[:i])
        dists.extend([1 - x for x in sims])
    clusters = cluster_mod.ClusterData(dists, nfps, float(threshold), isDistData=True)
    out_clusters = [
        {"centroid": valid_smiles[c[0]], "members": [valid_smiles[i] for i in c], "size": len(c)}
        for c in clusters
    ]
    return result(
        threshold=float(threshold),
        radius=int(radius),
        n_bits=int(n_bits),
        n_molecules=len(valid_smiles),
        n_clusters=len(out_clusters),
        clusters=out_clusters,
    )


run = skill_run(
    {
        "tanimoto": tanimoto,
        "dice": dice,
        "most_similar": most_similar,
        "cluster_butina": cluster_butina,
    }
)

register_skill("molecular_similarity", run)
