"""harmony skill: batch-effect correction with Harmony.

Uses ``harmonypy`` when installed; otherwise falls back to a numpy
least-squares batch regression on PCA scores (Harmony-like linear
correction of the embedding).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import has_module, optional_import, result, skill_run


def _matrix(data: Any) -> tuple[pd.DataFrame, list[str]]:
    df = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
    num = df.select_dtypes(include="number")
    if num.empty:
        raise ValueError("harmony requires at least one numeric column")
    return num, [str(c) for c in num.columns]


def _pca_scores(x: np.ndarray, n_components: int) -> np.ndarray:
    x = x - x.mean(axis=0)
    _, _, vt = np.linalg.svd(x, full_matrices=False)
    return x @ vt[:n_components].T


def _regress_out_batch(scores: np.ndarray, batch_codes: np.ndarray) -> np.ndarray:
    """Remove the linear batch component from embedding via least squares."""
    design = np.column_stack([np.ones(len(batch_codes)),
                              pd.get_dummies(batch_codes).to_numpy()[:, 1:]])
    coef, *_ = np.linalg.lstsq(design, scores, rcond=None)
    corrected = scores - design[:, 1:] @ coef[1:]
    return corrected


def correct(data: Any, batch: list[Any], n_components: int = 20,
            **kwargs) -> dict[str, Any]:
    """Correct batch effects in a data matrix (samples x features).

    ``batch`` is a per-row batch label list. Returns corrected embedding.
    Uses harmonypy when available, else a numpy PCA + least-squares fallback.
    """
    num, cols = _matrix(data)
    batch = list(batch)
    if len(batch) != len(num):
        raise ValueError("'batch' must have one label per row")
    n_components = max(1, min(n_components, num.shape[0] - 1, num.shape[1]))

    x = num.to_numpy(dtype=float)
    z = _pca_scores(x, n_components)
    backend = "harmonypy"
    if has_module("harmonypy"):
        hm = optional_import("harmonypy")
        meta = pd.DataFrame({"batch": batch})
        ho = hm.run_harmony(z, meta, ["batch"], **kwargs)
        corrected = np.asarray(ho.Z_corr).T
    else:
        backend = "numpy-least-squares"
        codes = pd.Categorical(batch).codes
        corrected = _regress_out_batch(z, codes)
    return result(
        backend=backend,
        n_rows=int(num.shape[0]),
        n_features=len(cols),
        n_components=int(n_components),
        batches=sorted({str(b) for b in batch}),
        embedding=corrected.tolist(),
    )


def pca_before_after(data: Any, batch: list[Any],
                     n_components: int = 10) -> dict[str, Any]:
    """Compare batch variance in PCA space before vs after correction."""
    num, _ = _matrix(data)
    batch = list(batch)
    if len(batch) != len(num):
        raise ValueError("'batch' must have one label per row")
    n_components = max(1, min(n_components, num.shape[0] - 1, num.shape[1]))

    x = num.to_numpy(dtype=float)
    x = x - x.mean(axis=0)
    _, _, vt = np.linalg.svd(x, full_matrices=False)
    comps = vt[:n_components]
    before = x @ comps.T

    corr = correct(data, batch, n_components=n_components)
    after = np.asarray(corr["embedding"], dtype=float)

    def batch_variance(scores: np.ndarray) -> dict[str, float]:
        df = pd.DataFrame(scores)
        codes = pd.Categorical(batch)
        per_pc = []
        for c in df.columns:
            grand = float(df[c].var())
            if grand == 0:
                per_pc.append(0.0)
                continue
            within = df.groupby(codes, observed=True)[c].var().mean()
            per_pc.append(float(max(0.0, grand - within) / grand))
        return {
            "per_pc": per_pc,
            "mean_batch_variance_fraction": float(np.mean(per_pc)),
        }

    return result(
        n_components=int(n_components),
        before=batch_variance(before),
        after=batch_variance(after),
        backend=corr["backend"],
    )


_OPS = {"correct": correct, "pca_before_after": pca_before_after}

run = skill_run(_OPS)
register_skill("harmony", run)
