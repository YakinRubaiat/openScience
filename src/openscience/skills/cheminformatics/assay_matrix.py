"""Fluorescence assay-compatibility skill.

Registers:
- ``assay_compatibility``

Spectral overlap is scored heuristically from excitation/emission
wavelengths using Gaussian band models.
"""

from __future__ import annotations

import math
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run

# Nominal 1-sigma widths (nm) for the Gaussian band model; ~15 nm half-width
# at half-maximum approximates typical small-molecule fluorophores.
_SIGMA_EX_NM = 18.0
_SIGMA_EM_NM = 22.0


def _gaussian(x: float, mu: float, sigma: float) -> float:
    if sigma <= 0:
        return 0.0
    return math.exp(-((x - mu) ** 2) / (2.0 * sigma * sigma))


def _overlap(a_mu: float, a_sigma: float, b_mu: float, b_sigma: float) -> float:
    """Gaussian overlap coefficient in [0, 1] (1 = identical bands)."""
    sigma2 = a_sigma**2 + b_sigma**2
    if sigma2 <= 0:
        return 0.0
    return math.exp(-((a_mu - b_mu) ** 2) / (2.0 * sigma2))


def _validate_dye(name: str, spec: dict[str, Any]) -> None:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Dye name must be a non-empty string")
    for key in ("ex_nm", "em_nm"):
        if key not in spec:
            raise ValueError(f"Dye {name!r} missing key {key!r}")
        val = float(spec[key])
        if not (200.0 <= val <= 900.0):
            raise ValueError(f"Dye {name!r} has {key}={val} outside 200-900 nm")


def check_pair(
    dye_a: dict[str, Any],
    dye_b: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    """Pairwise spectral-overlap heuristic between two fluorophores.

    Each dye is a dict ``{"name": str, "ex_nm": float, "em_nm": float}``.
    Returns a 0-1 emission-overlap score and a qualitative verdict:
    ``"good"`` (< 0.3), ``"caution"`` (< 0.6), ``"poor"`` (>= 0.6).
    """
    name_a = dye_a.get("name", "A")
    name_b = dye_b.get("name", "B")
    _validate_dye(name_a, dye_a)
    _validate_dye(name_b, dye_b)

    em_overlap = _overlap(
        float(dye_a["em_nm"]), _SIGMA_EM_NM, float(dye_b["em_nm"]), _SIGMA_EM_NM
    )
    ex_overlap = _overlap(
        float(dye_a["ex_nm"]), _SIGMA_EX_NM, float(dye_b["ex_nm"]), _SIGMA_EX_NM
    )
    if em_overlap >= 0.6:
        verdict = "poor"
    elif em_overlap >= 0.3:
        verdict = "caution"
    else:
        verdict = "good"

    return result(
        dye_a={**dye_a, "name": name_a},
        dye_b={**dye_b, "name": name_b},
        em_overlap=round(em_overlap, 3),
        ex_overlap=round(ex_overlap, 3),
        verdict=verdict,
    )


def panel_report(
    dyes: list[dict[str, Any]],
    **kwargs: Any,
) -> dict[str, Any]:
    """Report pairwise spectral-overlap across a panel of fluorophores."""
    dyes = list(dyes or [])
    if len(dyes) < 2:
        raise ValueError("panel_report requires at least two dyes")
    for d in dyes:
        _validate_dye(d.get("name", "?"), d)

    pairs = []
    pair_verdicts = []
    for i in range(len(dyes)):
        for j in range(i + 1, len(dyes)):
            pair = check_pair(dyes[i], dyes[j])
            del pair["status"]
            pairs.append(pair)
            pair_verdicts.append(pair["verdict"])

    max_overlap = max(p["em_overlap"] for p in pairs) if pairs else 0.0
    if pair_verdicts.count("poor") > 0:
        overall = "poor"
    elif pair_verdicts.count("caution") > 0:
        overall = "caution"
    else:
        overall = "good"
    return result(
        n_dyes=len(dyes),
        n_pairs=len(pairs),
        overall_verdict=overall,
        max_em_overlap=round(max_overlap, 3),
        pairs=pairs,
    )


run = skill_run(
    {
        "check_pair": check_pair,
        "panel_report": panel_report,
    }
)

register_skill("assay_compatibility", run)
