"""pyDOE2 skill: factorial designs (pyDOE2 if installed, pure-python fallback)."""

from __future__ import annotations

from itertools import product
from typing import Any

import numpy as np

from openscience.skills import register_skill
from openscience.skills._common import has_module, optional_import, result, skill_run


def full_factorial(levels: Any, **kwargs: Any) -> dict[str, Any]:
    """Full factorial design. ``levels`` is a list of per-factor level counts.

    Uses pyDOE2.fullfact when available, else a pure-python itertools product.
    """
    lvl = list(levels)
    if has_module("pyDOE2"):
        pyDOE2 = optional_import("pyDOE2")
        design = pyDOE2.fullfact(lvl)
        # fullfact returns coded 0..level-1 in arbitrary column order counting;
        # ensure int matrix shape (prod(levels), len(levels))
        design = np.asarray(design, dtype=int)
        backend = "pyDOE2"
    else:
        combos = list(product(*[range(n) for n in lvl]))
        design = np.asarray(combos, dtype=int)
        backend = "pure-python"

    return result(
        design_type="full_factorial",
        backend=backend,
        levels=[int(n) for n in lvl],
        n_factors=len(lvl),
        n_runs=int(design.shape[0]),
        design=design.tolist(),
    )


def fractional_factorial(
    levels: Any | None = None,
    gen: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Fractional factorial for 2-level factors via pyDOE2.fracfact.

    Falls back to the full factorial when pyDOE2 is unavailable, no generator
    string is given, or the generator fails.
    """
    if gen is not None and has_module("pyDOE2"):
        pyDOE2 = optional_import("pyDOE2")
        try:
            design = np.asarray(pyDOE2.fracfact(gen), dtype=int)
            n_factors = design.shape[1]
            return result(
                design_type="fractional_factorial",
                backend="pyDOE2",
                generator=gen,
                n_factors=n_factors,
                n_runs=int(design.shape[0]),
                levels=[2] * n_factors,
                design=design.tolist(),
            )
        except Exception:  # noqa: BLE001 - bad generator string; fall through
            pass

    # Fallback: full factorial over the given (or inferred) 2-level factors.
    if levels is None:
        if gen is not None:
            # count distinct letters in the generator string
            letters = sorted({c for c in gen if c.isalpha()})
            levels = [2] * len(letters)
        else:
            raise ValueError("fractional_factorial requires levels or a generator string")
    out = full_factorial(levels)
    out["design_type"] = "fractional_factorial_full_fallback"
    if gen is not None:
        out["generator"] = gen
        out["fallback_reason"] = "pyDOE2 unavailable or generator failed"
    return out


def design_matrix_df(design: Any, factor_names: Any | None = None, **kwargs: Any) -> dict[str, Any]:
    """Convert a coded design matrix to a pandas DataFrame (returned as records)."""
    import pandas as pd

    mat = np.asarray(design, dtype=float)
    if mat.ndim == 1:
        mat = mat.reshape(-1, 1)
    n_factors = mat.shape[1]
    names = list(factor_names) if factor_names else [f"factor_{i + 1}" for i in range(n_factors)]
    if len(names) != n_factors:
        raise ValueError(f"factor_names has {len(names)} entries but design has {n_factors} columns")
    df = pd.DataFrame(mat, columns=names)
    return result(
        n_runs=int(mat.shape[0]),
        n_factors=n_factors,
        columns=names,
        records=df.to_dict(orient="records"),
    )


run = skill_run(
    {
        "full_factorial": full_factorial,
        "fractional_factorial": fractional_factorial,
        "design_matrix_df": design_matrix_df,
    }
)

register_skill("pyDOE2", run)
