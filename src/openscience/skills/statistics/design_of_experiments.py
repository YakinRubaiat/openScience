"""Design-of-experiments helpers: randomization, blocking, alias structure."""

from __future__ import annotations

from typing import Any

import numpy as np

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run


def randomize_runs(design: Any, seed: int | None = None, **kwargs: Any) -> dict[str, Any]:
    """Randomly permute the run order of a design matrix."""
    mat = np.asarray(design)
    rng = np.random.default_rng(seed)
    order = rng.permutation(mat.shape[0])
    return result(
        n_runs=int(mat.shape[0]),
        seed=seed,
        run_order=order.tolist(),
        design=mat[order].tolist(),
    )


def block_design(design: Any, n_blocks: int = 2, seed: int | None = None, **kwargs: Any) -> dict[str, Any]:
    """Assign runs to blocks (round-robin over a randomized run order)."""
    mat = np.asarray(design)
    n = mat.shape[0]
    if not 1 <= n_blocks <= n:
        raise ValueError(f"n_blocks must be in [1, {n}], got {n_blocks}")
    rng = np.random.default_rng(seed)
    order = rng.permutation(n)
    blocks = np.empty(n, dtype=int)
    blocks[order] = np.arange(n) % n_blocks
    return result(
        n_runs=int(n),
        n_blocks=int(n_blocks),
        seed=seed,
        block_labels=blocks.tolist(),
        block_sizes=[int((blocks == b).sum()) for b in range(n_blocks)],
        design=mat.tolist(),
    )


def alias_structure(design: Any, **kwargs: Any) -> dict[str, Any]:
    """Pairwise column correlation as a simple confounding/alias report.

    Pairs with |r| near 1 are aliased (confounded) in the design.
    """
    import pandas as pd

    mat = np.asarray(design, dtype=float)
    if mat.ndim == 1:
        mat = mat.reshape(-1, 1)
    n_factors = mat.shape[1]
    corr = np.corrcoef(mat, rowvar=False) if n_factors > 1 else np.ones((1, 1))
    pairs = []
    for i in range(n_factors):
        for j in range(i + 1, n_factors):
            pairs.append({"factor_i": i, "factor_j": j, "correlation": float(corr[i, j])})
    # pandas cross-tab of unique level combos per pair -> alias table summary
    _ = pd.DataFrame(mat).corr()  # noqa: F841 - consistent numeric handling
    return result(
        n_runs=int(mat.shape[0]),
        n_factors=n_factors,
        correlation_matrix=corr.tolist(),
        pairwise_correlations=pairs,
        aliased_pairs=[p for p in pairs if abs(p["correlation"]) > 0.99],
    )


run = skill_run(
    {
        "randomize_runs": randomize_runs,
        "block_design": block_design,
        "alias_structure": alias_structure,
    }
)

register_skill("design_of_experiments", run)
