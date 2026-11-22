"""Reagent lookup skill backed by an embedded mini-catalog.

Registers:
- ``reagent_database``
"""

from __future__ import annotations

import re
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run

# Mini embedded catalog of ~40 commonly used wet-lab reagents.
# Each entry: (name, cas, category, hazard_keywords, notes)
_CATALOG: list[dict[str, Any]] = [
    {"name": "Sodium chloride", "cas": "7647-14-5", "category": "salt", "hazards": [], "notes": "Common saline buffer component."},
    {"name": "Tris base", "cas": "77-86-1", "category": "buffer", "hazards": ["irritant"], "notes": "Tris(hydroxymethyl)aminomethane."},
    {"name": "EDTA disodium", "cas": "139-33-3", "category": "chelator", "hazards": ["irritant"], "notes": "Divalent-cation chelator."},
    {"name": "SDS", "cas": "151-21-3", "category": "detergent", "hazards": ["irritant", "corrosive"], "notes": "Sodium dodecyl sulfate."},
    {"name": "Triton X-100", "cas": "9002-93-1", "category": "detergent", "hazards": ["irritant"], "notes": "Nonionic surfactant."},
    {"name": "Tween 20", "cas": "9005-64-5", "category": "detergent", "hazards": [], "notes": "Polysorbate 20."},
    {"name": "DMSO", "cas": "67-68-5", "category": "solvent", "hazards": ["skin-penetrant"], "notes": "Dimethyl sulfoxide."},
    {"name": "Ethanol absolute", "cas": "64-17-5", "category": "solvent", "hazards": ["flammable"], "notes": "ACS reagent grade."},
    {"name": "Methanol", "cas": "67-56-1", "category": "solvent", "hazards": ["flammable", "toxic"], "notes": "Methyl alcohol."},
    {"name": "Acetonitrile", "cas": "75-05-8", "category": "solvent", "hazards": ["flammable", "toxic"], "notes": "HPLC common organic modifier."},
    {"name": "Chloroform", "cas": "67-66-3", "category": "solvent", "hazards": ["toxic", "carcinogen"], "notes": "Use in fume hood."},
    {"name": "Isopropanol", "cas": "67-63-0", "category": "solvent", "hazards": ["flammable"], "notes": "2-Propanol."},
    {"name": "Acetone", "cas": "67-64-1", "category": "solvent", "hazards": ["flammable", "irritant"], "notes": "Cleaning solvent."},
    {"name": "Hydrochloric acid", "cas": "7647-01-0", "category": "acid", "hazards": ["corrosive"], "notes": "Strong mineral acid."},
    {"name": "Sulfuric acid", "cas": "7664-93-9", "category": "acid", "hazards": ["corrosive"], "notes": "Strong mineral acid."},
    {"name": "Nitric acid", "cas": "7697-37-2", "category": "acid", "hazards": ["corrosive", "oxidizer"], "notes": "Strong mineral acid."},
    {"name": "Sodium hydroxide", "cas": "1310-73-2", "category": "base", "hazards": ["corrosive"], "notes": "Strong base."},
    {"name": "Potassium hydroxide", "cas": "1310-58-3", "category": "base", "hazards": ["corrosive"], "notes": "Strong base."},
    {"name": "Phenol", "cas": "108-95-2", "category": "solvent", "hazards": ["toxic", "corrosive"], "notes": "Handle with PPE."},
    {"name": "Formaldehyde 37%", "cas": "50-00-0", "category": "fixative", "hazards": ["toxic", "carcinogen", "corrosive"], "notes": "Paraformaldehyde liquid form."},
    {"name": "Paraformaldehyde", "cas": "30525-89-4", "category": "fixative", "hazards": ["toxic", "irritant"], "notes": "Polymerized formaldehyde."},
    {"name": "Glutaraldehyde", "cas": "111-30-8", "category": "fixative", "hazards": ["toxic", "corrosive"], "notes": "EM secondary fixative."},
    {"name": "Ethidium bromide", "cas": "1239-45-8", "category": "dye", "hazards": ["mutagen", "toxic"], "notes": "Nucleic-acid intercalator."},
    {"name": "SYBR Green I", "cas": "163795-75-3", "category": "dye", "hazards": ["toxic"], "notes": "qPCR fluorescent dye."},
    {"name": "DAPI", "cas": "28718-90-3", "category": "dye", "hazards": ["mutagen"], "notes": "DNA minor-groove blue fluorophore."},
    {"name": "Hoechst 33342", "cas": "23491-52-3", "category": "dye", "hazards": ["mutagen"], "notes": "Cell-permeant DNA stain."},
    {"name": "Propidium iodide", "cas": "25535-16-4", "category": "dye", "hazards": ["mutagen"], "notes": "Viability dye."},
    {"name": "Penicillin-streptomycin", "cas": "9037-79-2", "category": "antibiotic", "hazards": [], "notes": "Cell-culture supplement."},
    {"name": "Kanamycin", "cas": "8063-07-8", "category": "antibiotic", "hazards": ["irritant"], "notes": "Aminoglycoside selection marker."},
    {"name": "Ampicillin", "cas": "69-53-4", "category": "antibiotic", "hazards": [], "notes": "Beta-lactam selection marker."},
    {"name": "HEPES", "cas": "7365-45-9", "category": "buffer", "hazards": [], "notes": "Zwitterionic buffer pH 6.8-8.2."},
    {"name": "MES", "cas": "4432-31-9", "category": "buffer", "hazards": [], "notes": "Zwitterionic buffer pH 5.5-6.7."},
    {"name": "DTT", "cas": "3483-12-3", "category": "reductant", "hazards": ["irritant"], "notes": "Dithiothreitol reducing agent."},
    {"name": "TCEP", "cas": "51805-45-9", "category": "reductant", "hazards": ["irritant"], "notes": "Tris(2-carboxyethyl)phosphine."},
    {"name": "Hydrogen peroxide 30%", "cas": "7722-84-1", "category": "oxidizer", "hazards": ["corrosive", "oxidizer"], "notes": "Strong oxidizer."},
    {"name": "Sodium azide", "cas": "26628-22-8", "category": "preservative", "hazards": ["toxic"], "notes": "Antimicrobial preservative."},
    {"name": "Glycerol", "cas": "56-81-5", "category": "cryoprotectant", "hazards": [], "notes": "Cryoprotectant, density 1.26 g/mL."},
    {"name": "Urea", "cas": "57-13-6", "category": "denaturant", "hazards": [], "notes": "Protein denaturant."},
    {"name": "Guanidinium chloride", "cas": "50-01-1", "category": "denaturant", "hazards": ["irritant"], "notes": "Chaotrope."},
    {"name": "IPTG", "cas": "367-93-1", "category": "inducer", "hazards": [], "notes": "lac~operon inducer."},
]

# Hazard keyword -> short flag.
_HAZARD_KEYWORDS = {
    "carcinogen": "carcinogen",
    "mutagen": "mutagen",
    "toxic": "toxic",
    "corrosive": "corrosive",
    "flammable": "flammable",
    "oxidizer": "oxidizer",
    "irritant": "irritant",
    "skin-penetrant": "skin-penetrant",
}


def _find_reagent(query: str) -> dict[str, Any] | None:
    if not query or not query.strip():
        return None
    q = query.strip().lower()
    for entry in _CATALOG:
        if entry["name"].lower() == q:
            return entry
    for entry in _CATALOG:
        if entry["cas"].lower() == q:
            return entry
    return None


def lookup(query: str, **kwargs: Any) -> dict[str, Any]:
    """Look up a reagent by name or CAS number."""
    entry = _find_reagent(query)
    if entry is None:
        return result(found=False, query=query, entry=None)
    return result(found=True, query=query, entry=dict(entry))


def search_by_name(substring: str, limit: int = 10, **kwargs: Any) -> dict[str, Any]:
    """Free-text substring search across reagent names."""
    if not substring or not substring.strip():
        raise ValueError("Empty substring")
    q = substring.strip().lower()
    hits = [e for e in _CATALOG if q in e["name"].lower()]
    hits = hits[: int(limit)]
    return result(
        query=substring,
        n_hits=len(hits),
        hits=[dict(e) for e in hits],
    )


_HAZARDOUS_WORDLIST = [
    r"\b(carcinogen|mutagen|teratogen)\b",
    r"\b(toxic|poison|venom)\b",
    r"\b(corrosive|caustic)\b",
    r"\b(flammable|pyrophoric|combustible)\b",
    r"\b(oxidizer|oxidising|oxidizing)\b",
    r"\b(irritant|sensiti[sz]er)\b",
    r"\b(radioactive|radionuclide)\b",
    r"\b(biohazard|infectious|pathogen)\b",
    r"\b(explosive|detonation)\b",
]
_HAZARDOUS_RE = re.compile("|".join(_HAZARDOUS_WORDLIST), re.IGNORECASE)


def hazardous_flag(reagent_text: str, **kwargs: Any) -> dict[str, Any]:
    """Heuristic hazardous-content flag from free text.

    Scans the reagent name, CAS number, or description against a keyword
    list plus the embedded catalog's hazard tags.
    """
    if not reagent_text or not reagent_text.strip():
        raise ValueError("Empty reagent_text")
    text = reagent_text.strip()

    text_hazards = sorted(set(m.group(0).lower() for m in _HAZARDOUS_RE.finditer(text)))
    catalog_hits: list[str] = []
    entry = _find_reagent(text)
    if entry is not None:
        catalog_hazards = list(entry.get("hazards", []))
        catalog_hits = [entry["name"]]
    else:
        catalog_hazards = []
        lowered = text.lower()
        for e in _CATALOG:
            if e["name"].lower() in lowered:
                catalog_hazards.extend(e.get("hazards", []))
                catalog_hits.append(e["name"])

    flags = sorted({*text_hazards, *[h.lower() for h in catalog_hazards]})
    return result(
        reagent_text=reagent_text,
        hazardous=bool(flags),
        hazard_flags=flags,
        catalog_hits=catalog_hits,
    )


run = skill_run(
    {
        "lookup": lookup,
        "search_by_name": search_by_name,
        "hazardous_flag": hazardous_flag,
    }
)

register_skill("reagent_database", run)
