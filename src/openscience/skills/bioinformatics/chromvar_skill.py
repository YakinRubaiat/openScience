"""chromVAR-style motif accessibility deviation skill (pure numpy).

chromVAR computes per-cell bias-corrected deviation of chromatin
accessibility at motif-containing peaks. This skill implements the core
math without the R/Bioconductor dependency:

- ``motif_bias_scores``      — z-score each cell's total accessibility at
  motif-matched peaks against all cells
- ``accessibility_deviation``— per cell x motif deviation of observed vs
  expected (fraction of reads in motif peaks minus genome-wide expectation)
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import unwrap


def _matrix(counts=None, kw=None) -> pd.DataFrame:
    kw = kw or {}
    m = counts if counts is not None else kw.get("counts")
    if m is None:
        raise ValueError("Provide 'counts' (peaks x cells matrix)")
    return pd.DataFrame(m, dtype=float)


def motif_bias_scores(counts=None, motif_matches=None, **kwargs: Any):
    """Per-cell z-score of summed accessibility over peaks matching a motif."""
    kw = unwrap(kwargs)
    df = _matrix(counts, kwargs)
    matches = motif_matches if motif_matches is not None else kw.get("motif_matches")
    if matches is None:
        raise ValueError("motif_bias_scores requires 'motif_matches' (peak names or bool mask)")
    peaks = np.asarray(df.index.astype(str))
    if isinstance(matches, (list, tuple, set, np.ndarray)) and len(matches) and isinstance(next(iter(matches)), (bool, np.bool_)):
        mask = np.asarray(list(matches), dtype=bool)
        if mask.shape[0] != df.shape[0]:
            raise ValueError("Boolean motif_matches mask must equal number of peaks")
    else:
        mset = {str(x) for x in matches}
        mask = np.array([p in mset for p in peaks])
    if not mask.any():
        raise ValueError("No motif-matched peaks found in matrix index")

    matched = df.to_numpy(dtype=float)[mask]
    per_cell = matched.sum(axis=0)
    mu, sd = per_cell.mean(), per_cell.std(ddof=1) if df.shape[1] > 1 else 1.0
    sd = sd if sd > 0 else 1.0
    z = (per_cell - mu) / sd
    cells = [str(c) for c in df.columns]
    return {
        "n_motif_peaks": int(mask.sum()),
        "n_cells": int(df.shape[1]),
        "scores": [
            {"cell": c, "raw_accessibility": float(v), "z_score": float(zz)}
            for c, v, zz in zip(cells, per_cell, z)
        ],
    }


def accessibility_deviation(counts=None, motif_peak_sets=None, **kwargs: Any):
    """Per-cell, per-motif deviation: observed fraction of reads in motif
    peaks minus the expected fraction (same for all cells from column means)."""
    kw = unwrap(kwargs)
    df = _matrix(counts, kwargs)
    sets = motif_peak_sets if motif_peak_sets is not None else kw.get("motif_peak_sets")
    if not sets:
        raise ValueError("accessibility_deviation requires 'motif_peak_sets' (dict motif -> peak names)")

    mat = df.to_numpy(dtype=float)
    peaks = np.asarray(df.index.astype(str))
    totals = mat.sum(axis=0)
    totals = np.where(totals > 0, totals, 1.0)
    # Expected profile: average per-peak fraction across cells
    expected_profile = (mat / totals).mean(axis=1)

    results = {}
    for motif, motif_peaks in sets.items():
        mset = {str(x) for x in motif_peaks}
        mask = np.array([p in mset for p in peaks])
        if not mask.any():
            continue
        observed = (mat[mask].sum(axis=0)) / totals
        expected = expected_profile[mask].sum()
        deviation = observed - expected
        results[str(motif)] = {
            "n_peaks": int(mask.sum()),
            "expected_fraction": float(expected),
            "cells": [
                {"cell": str(c), "observed_fraction": float(o), "deviation": float(d)}
                for c, o, d in zip(df.columns, observed, deviation)
            ],
            "mean_abs_deviation": float(np.abs(deviation).mean()),
        }
    return {
        "n_motifs": len(results),
        "n_cells": int(df.shape[1]),
        "motifs": results,
    }


def run(operation: str, **kwargs: Any):
    ops = {
        "motif_bias_scores": motif_bias_scores,
        "accessibility_deviation": accessibility_deviation,
    }
    fn = ops.get(operation)
    if fn is None:
        raise ValueError(f"chromVAR: unknown operation {operation!r}. Available: {sorted(ops)}")
    return fn(**kwargs)


register_skill("chromVAR", run)
