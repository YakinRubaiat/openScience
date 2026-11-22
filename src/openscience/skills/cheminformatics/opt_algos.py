"""Classical optimization wrappers (Nelder–Mead, grid search).

Registers:
- ``optimization_algorithms``
"""

from __future__ import annotations

import itertools
import math
from typing import Any, Callable

from openscience.skills import register_skill
from openscience.skills._common import optional_import, result, skill_run

_SCALAR_SAFE_GLOBALS = {
    "abs": abs,
    "min": min,
    "max": max,
    "sum": sum,
    "len": len,
    "pow": pow,
    "math": math,
}


def _to_objective(fn_or_expr: Any, params: list[str]) -> Callable[..., float]:
    if callable(fn_or_expr):
        return fn_or_expr
    if isinstance(fn_or_expr, str):
        expr = fn_or_expr.strip()
        if not expr:
            raise ValueError("Empty objective expression")
        code = compile(expr, "<objective>", "eval")

        def _obj(**kwargs):
            env = dict(_SCALAR_SAFE_GLOBALS)
            env.update(kwargs)
            return float(eval(code, {"__builtins__": {}}, env))  # noqa: S307 - sandboxed

        return _obj
    raise ValueError("objective_fn must be a callable or a math expression string")


def nelder_mead(
    objective_fn,
    x0: list[float],
    bounds: list[tuple[float, float]] | None = None,
    max_iter: int = 200,
    xatol: float = 1e-6,
    fatol: float = 1e-6,
    params: list[str] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Scipy Nelder–Mead minimization.

    ``objective_fn`` may be a callable taking ``**(param=value)`` for each
    entry in ``params`` (or a single positional vector when ``params`` is
    omitted), or a math expression evaluated against ``params`` names.
    """
    np = optional_import("numpy", "numpy")
    opt_mod = optional_import("scipy.optimize", "scipy")

    x0 = list(x0 or [])
    if not x0:
        raise ValueError("x0 must contain at least one starting coordinate")
    if params is None:
        params = [f"x{i}" for i in range(len(x0))]
    if len(params) != len(x0):
        raise ValueError("params and x0 must have the same length")

    obj_eval = _to_objective(objective_fn, params)

    def f(vec):
        vec = [float(v) for v in vec]
        kwargs_map = dict(zip(params, vec))
        return obj_eval(**kwargs_map)

    # Apply bounds via penalty so Nelder-Mead stays unconstrained.
    bounds_list = None
    if bounds:
        bounds_list = [tuple(b) for b in bounds]
        if len(bounds_list) != len(x0):
            raise ValueError("bounds and x0 must have the same length")

        def bounded_f(vec):
            for v, (lo, hi) in zip(vec, bounds_list):
                if not (lo <= v <= hi):
                    return 1e12 + sum((v - v) ** 2 for v in vec)  # large penalty
            return f(vec)

        f_to_use = bounded_f
    else:
        f_to_use = f

    opt_result = opt_mod.minimize(
        f_to_use,
        np.asarray(x0, dtype=float),
        method="Nelder-Mead",
        options={"maxiter": int(max_iter), "xatol": float(xatol), "fatol": float(fatol)},
    )
    x_out = [float(x) for x in opt_result.x]
    return result(
        success=bool(opt_result.success),
        message=str(opt_result.message),
        n_iter=int(getattr(opt_result, "nit", 0)),
        n_eval=int(getattr(opt_result, "nfev", 0)),
        x=x_out,
        fun=float(opt_result.fun),
        params=dict(zip(params, x_out)),
        history=[],
    )


def grid_search(
    objective_fn,
    grid: dict[str, list[float]],
    maximize: bool = False,
    **kwargs: Any,
) -> dict[str, Any]:
    """Cartesian grid search over named parameters."""
    items = sorted(grid.items())
    if not items:
        raise ValueError("grid must be a non-empty dict of param -> values")
    names = [k for k, _ in items]
    values = [list(map(float, v)) for _, v in items]
    if any(len(v) == 0 for v in values):
        raise ValueError("grid values must be non-empty")

    obj = _to_objective(objective_fn, names)
    results = []
    best_params = None
    best_value = None
    maximize = bool(maximize)
    for combo in itertools.product(*values):
        params_map = dict(zip(names, combo))
        value = float(obj(**params_map))
        results.append({"params": params_map, "value": value})
        if best_value is None or (value > best_value if maximize else value < best_value):
            best_value = value
            best_params = params_map
    return result(
        best_params=best_params,
        best_value=best_value,
        maximize=maximize,
        n_evaluations=len(results),
        results=results,
    )


def best_result(
    results: list[dict[str, Any]],
    objective: str = "value",
    maximize: bool = False,
    **kwargs: Any,
) -> dict[str, Any]:
    """Pick the best entry out of a prior search's ``results`` list."""
    if not results:
        raise ValueError("results must be a non-empty list")
    maximize = bool(maximize)
    key = objective
    best = None
    best_val = None
    for r in results:
        if key not in r:
            raise ValueError(f"Entry missing key {key!r}: {r!r}")
        val = float(r[key])
        if best_val is None or (val > best_val if maximize else val < best_val):
            best_val = val
            best = r
    return result(best=best, best_value=best_val, objective=objective, maximize=maximize)


run = skill_run(
    {
        "nelder_mead": nelder_mead,
        "grid_search": grid_search,
        "best_result": best_result,
    }
)

register_skill("optimization_algorithms", run)
