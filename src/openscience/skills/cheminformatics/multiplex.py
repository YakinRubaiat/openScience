"""Multiplex panel optimization skill.

Registers:
- ``multiplex_optimization``

Uses a greedy, channel-separation-maximizing selection over fluorophore
ex/em spectra.
"""

from __future__ import annotations

import math
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run

_SIGMA_EX_NM = 18.0
_SIGMA_EM_NM = 22.0


def _gauss_overlap(a_mu: float, a_sd: float, b_mu: float, b_sd: float) -> float:
    sd2 = a_sd**2 + b_sd**2
    if sd2 <= 0:
        return 0.0
    return math.exp(-((a_mu - b_mu) ** 2) / (2.0 * sd2))


def _validate_dye(name: str, spec: dict[str, Any]) -> None:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Dye name must be a non-empty string")
    for key in ("ex_nm", "em_nm"):
        if key not in spec:
            raise ValueError(f"Dye {name!r} missing {key!r}")
        val = float(spec[key])
        if not (200.0 <= val <= 900.0):
            raise ValueError(f"Dye {name!r} has {key}={val} outside 200-900 nm")


def _min_pairwise_overlap(a: dict[str, Any], b: dict[str, Any]) -> float:
    """Maximum overlap for a pair: take the worst (min ex, min em)."""
    em = _gauss_overlap(float(a["em_nm"]), _SIGMA_EM_NM, float(b["em_nm"]), _SIGMA_EM_NM)
    ex = _gauss_overlap(float(a["ex_nm"]), _SIGMA_EX_NM, float(b["ex_nm"]), _SIGMA_EX_NM)
    return max(em, ex)


def greedy_panel(
    candidates: list[dict[str, Any]],
    n_select: int,
    **kwargs: Any,
) -> dict[str, Any]:
    """Greedy channel-separation panel selection.

    At each step, adds the candidate whose *minimum* pairwise spectral
    overlap with the already-chosen panel is the smallest. Guarantees a
    deterministic panel for a given input order.
    """
    candidates = list(candidates or [])
    if n_select <= 0:
        raise ValueError("n_select must be positive")
    if len(candidates) < n_select:
        raise ValueError(f"Not enough candidates ({len(candidates)}) for n_select={n_select}")
    for d in candidates:
        _validate_dye(d.get("name", "?"), d)

    # Seed with the dye having the longest emission wavelength (heuristic).
    remaining = list(candidates)
    remaining.sort(key=lambda d: (-float(d["em_nm"]), d.get("name", "")))
    chosen: list[dict[str, Any]] = [remaining.pop(0)]

    while len(chosen) < n_select and remaining:
        best_idx = None
        best_score = None
        for idx, cand in enumerate(remaining):
            worst = max(_min_pairwise_overlap(cand, c) for c in chosen)
            name = cand.get("name", "")
            score = (worst, name)
            if best_score is None or score < best_score:
                best_score = score
                best_idx = idx
        if best_idx is None:
            break
        chosen.append(remaining.pop(best_idx))

    # Recompute min pairwise overlap across the final panel.
    final_worst = 0.0
    for i in range(len(chosen)):
        for j in range(i + 1, len(chosen)):
            final_worst = max(final_worst, _min_pairwise_overlap(chosen[i], chosen[j]))

    return result(
        n_select=len(chosen),
        selection_order=[d.get("name") for d in chosen],
        panel=chosen,
        max_pairwise_overlap=round(final_worst, 3),
        rationale="greedy min-max emission/excitation separation",
    )


def spillover_matrix(
    dyes: list[dict[str, Any]],
    **kwargs: Any,
) -> dict[str, Any]:
    """Pairwise emission-spillover matrix across a panel (diagonal = 1.0)."""
    dyes = list(dyes or [])
    if not dyes:
        raise ValueError("dyes must be a non-empty list")
    for d in dyes:
        _validate_dye(d.get("name", "?"), d)

    names = [d.get("name", "?") for d in dyes]
    matrix: list[list[float]] = []
    for a in dyes:
        row = []
        for b in dyes:
            row.append(
                round(
                    _gauss_overlap(
                        float(a["em_nm"]), _SIGMA_EM_NM, float(b["em_nm"]), _SIGMA_EM_NM
                    ),
                    4,
                )
            )
        matrix.append(row)

    return result(
        names=names,
        spillover_matrix=matrix,
        sigma_em_nm=_SIGMA_EM_NM,
        sigma_ex_nm=_SIGMA_EX_NM,
    )


run = skill_run(
    {
        "greedy_panel": greedy_panel,
        "spillover_matrix": spillover_matrix,
    }
)

register_skill("multiplex_optimization", run)
