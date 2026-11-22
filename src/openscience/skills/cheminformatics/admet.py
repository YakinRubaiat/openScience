"""ADMET rule-based filters skill.

Registers:
- ``admet_rules``
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


def ro5_violations(smiles: str, **kwargs: Any) -> dict[str, Any]:
    """Lipinski Rule-of-5 flags (MW, logP, HBD, HBA)."""
    mol = _mol_from_smiles(smiles)
    desc = optional_import("rdkit.Chem.Descriptors", "rdkit")
    crippen = optional_import("rdkit.Chem.Crippen", "rdkit")
    lip = optional_import("rdkit.Chem.Lipinski", "rdkit")

    mw = float(desc.MolWt(mol))
    logp = float(crippen.MolLogP(mol))
    hbd = int(lip.NumHDonors(mol))
    hba = int(lip.NumHAcceptors(mol))
    violations = []
    if mw > 500.0:
        violations.append("mw_gt_500")
    if logp > 5.0:
        violations.append("logp_gt_5")
    if hbd > 5:
        violations.append("hbd_gt_5")
    if hba > 10:
        violations.append("hba_gt_10")
    return result(
        smiles=smiles,
        mw=round(mw, 3),
        logp=round(logp, 3),
        hbd=hbd,
        hba=hba,
        violations=violations,
        violation_count=len(violations),
        passes=len(violations) == 0,
    )


def veber(smiles: str, **kwargs: Any) -> dict[str, Any]:
    """Veber oral-bioavailability filter (rotB <= 10, TPSA <= 140 A^2)."""
    mol = _mol_from_smiles(smiles)
    lip = optional_import("rdkit.Chem.Lipinski", "rdkit")
    desc = optional_import("rdkit.Chem.rdMolDescriptors", "rdkit")

    rot = int(lip.NumRotatableBonds(mol))
    tpsa = float(desc.CalcTPSA(mol))
    violations = []
    if rot > 10:
        violations.append("rotatable_gt_10")
    if tpsa > 140.0:
        violations.append("tpsa_gt_140")
    return result(
        smiles=smiles,
        rotatable_bonds=rot,
        tpsa=round(tpsa, 3),
        violations=violations,
        violation_count=len(violations),
        passes=len(violations) == 0,
    )


def ghose(smiles: str, **kwargs: Any) -> dict[str, Any]:
    """Ghose filter: MW, logP, atoms, molar refractivity window."""
    mol = _mol_from_smiles(smiles)
    desc = optional_import("rdkit.Chem.Descriptors", "rdkit")
    crippen = optional_import("rdkit.Chem.Crippen", "rdkit")

    mw = float(desc.MolWt(mol))
    logp = float(crippen.MolLogP(mol))
    mr = float(crippen.MolMR(mol))
    atoms = int(mol.GetNumAtoms())
    violations = []
    if not (160.0 <= mw <= 480.0):
        violations.append("mw_outside_160_480")
    if not (-0.4 <= logp <= 5.6):
        violations.append("logp_outside_-0.4_5.6")
    if not (40.0 <= mr <= 130.0):
        violations.append("mr_outside_40_130")
    if not (20 <= atoms <= 70):
        violations.append("atom_count_outside_20_70")
    return result(
        smiles=smiles,
        mw=round(mw, 3),
        logp=round(logp, 3),
        mr=round(mr, 3),
        heavy_atoms=atoms,
        violations=violations,
        violation_count=len(violations),
        passes=len(violations) == 0,
    )


def egan(smiles: str, **kwargs: Any) -> dict[str, Any]:
    """Egan (TPSA + logP) absorption model: TPSA<=131.6 AND logP<=5.88."""
    mol = _mol_from_smiles(smiles)
    desc = optional_import("rdkit.Chem.rdMolDescriptors", "rdkit")
    crippen = optional_import("rdkit.Chem.Crippen", "rdkit")

    tpsa = float(desc.CalcTPSA(mol))
    logp = float(crippen.MolLogP(mol))
    violations = []
    if tpsa > 131.6:
        violations.append("tpsa_gt_131.6")
    if logp > 5.88:
        violations.append("logp_gt_5.88")
    return result(
        smiles=smiles,
        tpsa=round(tpsa, 3),
        logp=round(logp, 3),
        violations=violations,
        violation_count=len(violations),
        passes=len(violations) == 0,
    )


def _pains_catalog_flags(mol) -> dict[str, list[str]] | None:
    """Hit each PAINS sub-catalog (A/B/C) using rdkit's FilterCatalog.

    Returns ``None`` if the FilterCatalog or PAINS sub-catalogs are
    unavailable in the installed RDKit.
    """
    try:
        catalog_params_cls = optional_import("rdkit.Chem.FilterCatalog", "rdkit")
    except RuntimeError:
        return None
    ParamsCls = getattr(catalog_params_cls, "FilterCatalogParams", None)
    if ParamsCls is None:
        return None
    filters_enum = getattr(ParamsCls, "FilterCatalogs", None)
    if filters_enum is None:
        return None
    results: dict[str, list[str]] = {}
    for name in ("PAINS_A", "PAINS_B", "PAINS_C"):
        flag = getattr(filters_enum, name, None)
        if flag is None:
            return None
        params = ParamsCls()
        params.AddCatalog(flag)
        catalog = catalog_params_cls.FilterCatalog(params)
        entries = catalog.GetMatches(mol)
        results[name] = [e.GetDescription() for e in entries]
    return results


def pains_alerts(smiles: str, **kwargs: Any) -> dict[str, Any]:
    """Embedded PAINS substructure alerts (Baell & Holloway).

    Uses ``rdkit.Chem.FilterCatalogParams.FilterCatalogs.PAINS_*`` when the
    installed RDKit ships the struct-alert catalogs (RDKit >= 2018.03).
    Falls back to a curated subset of ~30 PAINS SMARTS otherwise.
    """
    mol = _mol_from_smiles(smiles)
    alerts = _pains_catalog_flags(mol)
    if alerts is None:
        alerts = _pains_embedded_flags(mol)
        source = "embedded_smarts"
    else:
        source = "rdkit_filter_catalog"
    flat = [s for hits in alerts.values() for s in hits]
    return result(
        smiles=smiles,
        source=source,
        alerts=alerts,
        alert_count=len(flat),
        passes=len(flat) == 0,
    )


_PAINS_EMBEDDED = [
    ("quinones", "c1c(=O)c=cc(=O)c=1"),
    ("catechols", "c1cc(O)c(O)cc1"),
    ("hydroquinones", "c1cc(O)ccc1O"),
    ("rhodanines", "C1=CNC=S1"),
    ("anilines", "c1ccccc1N"),
    ("acyl_hydrazides", "C(=O)NN"),
    ("enone_Michael_acceptors", "C=CC(=O)"),
    ("nitroaromatics", "c[N+](=O)[O-]"),
    ("aldehydes", "C(=O)H"),
    ("aliphatic_long_chain", "CCCCCCCC"),
    ("catechol_mono_amines", "Oc1cccc(O)c1N"),
    ("redox_cyclers", "c1ccncc1"),
]


def _pains_embedded_flags(mol) -> dict[str, list[str]]:
    chem = optional_import("rdkit.Chem", "rdkit")
    hits: dict[str, list[str]] = {}
    for name, smarts in _PAINS_EMBEDDED:
        patt = chem.MolFromSmarts(smarts)
        if patt is None:
            continue
        if mol.HasSubstructMatch(patt):
            hits[name] = [smarts]
    return hits


run = skill_run(
    {
        "ro5_violations": ro5_violations,
        "veber": veber,
        "ghose": ghose,
        "egan": egan,
        "pains_alerts": pains_alerts,
    }
)

register_skill("admet_rules", run)
