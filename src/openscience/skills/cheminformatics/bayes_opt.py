"""Pure-python 1-D Bayesian optimization (toy GP with RBF kernel).

Registers:
- ``bayesian_optimization``

This is intentionally minimal: a small closed-form GP (rbf kernel +
Cholesky posterior) with Expected Improvement acquisition over a fixed
1-D grid. It's a teaching tool, not a production optimizer.
"""

from __future__ import annotations

import math
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import optional_import, result, skill_run


def _rbf_kernel(x_1: float, x_2: float, length_scale: float, sigma_f: float) -> float:
    return sigma_f**2 * math.exp(-(x_1 - x_2) ** 2 / (2.0 * length_scale**2))


class _RbfGP:
    """Closed-form Gaussian Process with RBF kernel and Gaussian noise."""

    def __init__(self, length_scale: float = 0.2, sigma_f: float = 1.0, noise: float = 1e-6):
        if length_scale <= 0 or sigma_f <= 0 or noise <= 0:
            raise ValueError("length_scale, sigma_f, noise must all be > 0")
        self.length_scale = float(length_scale)
        self.sigma_f = float(sigma_f)
        self.noise = float(noise)
        self.x_train: list[float] = []
        self.y_train: list[float] = []
        self._L = None  # cached Cholesky factor
        self._alpha = None

    def fit(self, x_train: list[float], y_train: list[float]) -> None:
        np = optional_import("numpy", "numpy")
        if len(x_train) != len(y_train):
            raise ValueError("x_train and y_train must have the same length")
        if not x_train:
            raise ValueError("x_train must be non-empty")
        x_arr = np.asarray(x_train, dtype=float)
        y_arr = np.asarray(y_train, dtype=float)
        n = len(x_train)
        K = np.zeros((n, n), dtype=float)
        for i in range(n):
            for j in range(n):
                K[i, j] = _rbf_kernel(x_arr[i], x_arr[j], self.length_scale, self.sigma_f)
        K += self.noise * np.eye(n)
        # Numerical jitter for stability.
        for _ in range(5):
            try:
                self._L = np.linalg.cholesky(K)
                break
            except np.linalg.LinAlgError:
                K += 1e-8 * np.eye(n)
        else:
            raise RuntimeError("GP covariance Cholesky failed even with jitter")
        self._alpha = np.linalg.solve(self._L.T, np.linalg.solve(self._L, y_arr - y_arr.mean()))
        self._y_mean = float(y_arr.mean())
        self.x_train = list(x_train)
        self.y_train = list(y_train)

    def predict(self, x_new: list[float]) -> tuple[list[float], list[float]]:
        np = optional_import("numpy", "numpy")
        if self._L is None or self._alpha is None:
            raise RuntimeError("GP not fitted; call fit() first")
        x_new_arr = np.asarray(x_new, dtype=float)
        x_train = np.asarray(self.x_train, dtype=float)
        K_s = np.zeros((len(x_new_arr), len(x_train)), dtype=float)
        for i, xi in enumerate(x_new_arr):
            for j, xj in enumerate(x_train):
                K_s[i, j] = _rbf_kernel(xi, xj, self.length_scale, self.sigma_f)
        K_ss = np.zeros((len(x_new_arr), len(x_new_arr)), dtype=float)
        for i, xi in enumerate(x_new_arr):
            for j, xj in enumerate(x_new_arr):
                K_ss[i, j] = _rbf_kernel(xi, xj, self.length_scale, self.sigma_f)
        K_ss += self.noise * np.eye(len(x_new_arr))
        mu = self._y_mean + K_s @ self._alpha
        v = np.linalg.solve(self._L, K_s.T)
        cov = K_ss - v.T @ v
        var = np.maximum(np.diag(cov), 1e-12)
        std = np.sqrt(var)
        return mu.tolist(), std.tolist()


def _expected_improvement(mu: float, std: float, best: float, xi: float = 0.01) -> float:
    """Expected improvement for minimization."""
    if std <= 0:
        return 0.0
    imp = best - mu - xi
    z = imp / std
    phi = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    pdf = math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)
    return imp * phi + std * pdf


def gp_ei_1d(
    x_train: list[float],
    y_train: list[float],
    x_candidates: list[float],
    length_scale: float = 0.2,
    sigma_f: float = 1.0,
    noise: float = 1e-6,
    xi: float = 0.01,
    **kwargs: Any,
) -> dict[str, Any]:
    """1-D GP posterior + expected improvement over a grid of candidates."""
    if not x_train or not y_train:
        raise ValueError("x_train and y_train must be non-empty")
    if len(x_train) != len(y_train):
        raise ValueError("x_train and y_train must have the same length")
    if not x_candidates:
        raise ValueError("x_candidates must be non-empty")

    gp = _RbfGP(length_scale=length_scale, sigma_f=sigma_f, noise=noise)
    gp.fit(x_train, y_train)
    mu, std = gp.predict(x_candidates)
    best = float(min(y_train))
    ei = [_expected_improvement(m, s, best, xi=xi) for m, s in zip(mu, std)]
    best_i = max(range(len(ei)), key=lambda i: ei[i])
    return result(
        x_candidates=list(x_candidates),
        mean=mu,
        std=std,
        ei=ei,
        next_x=float(x_candidates[best_i]),
        next_ei=float(ei[best_i]),
        y_best=best,
    )


def suggest(
    objective_fn,
    bounds: list[float] | tuple[float, float],
    n_steps: int = 5,
    n_init: int = 3,
    xi: float = 0.01,
    length_scale: float = 0.2,
    **kwargs: Any,
) -> dict[str, Any]:
    """Greedy Bayesian sampling loop over a 1-D objective.

    ``objective_fn`` may be a callable taking ``x`` or a math-expression
    string referencing ``x``.
    """
    if not bounds or len(bounds) != 2:
        raise ValueError("bounds must be [min, max]")
    lo, hi = float(bounds[0]), float(bounds[1])
    if hi <= lo:
        raise ValueError("bounds must satisfy min < max")
    if n_steps <= 0:
        raise ValueError("n_steps must be positive")
    if n_init < 2:
        raise ValueError("n_init must be >= 2")

    obj = objective_fn
    if isinstance(obj, str):
        expr = obj.strip()
        if not expr:
            raise ValueError("Empty objective expression")
        code = compile(expr, "<objective>", "eval")

        def _fn(x):
            return float(eval(code, {"__builtins__": {"math": math}}, {"x": float(x)}))  # noqa: S307

        obj = _fn

    # Initial Sobol-like grid for reproducibility (without scipy).
    x_train = [lo + (i + 0.5) * (hi - lo) / n_init for i in range(n_init)]
    y_train = [float(obj(x)) for x in x_train]
    history = [{"x": x, "y": y, "stage": "init"} for x, y in zip(x_train, y_train)]

    for step in range(int(n_steps)):
        n_cand = 128
        candidates = [lo + (i + 0.5) * (hi - lo) / n_cand for i in range(n_cand)]
        step_info = gp_ei_1d(
            x_train=x_train,
            y_train=y_train,
            x_candidates=candidates,
            length_scale=length_scale,
            xi=xi,
        )
        next_x = step_info["next_x"]
        next_y = float(obj(next_x))
        x_train.append(next_x)
        y_train.append(next_y)
        history.append({"x": next_x, "y": next_y, "stage": f"ei_step_{step}"})

    best_i = min(range(len(y_train)), key=lambda i: y_train[i])
    return result(
        best_x=float(x_train[best_i]),
        best_y=float(y_train[best_i]),
        x_train=x_train,
        y_train=y_train,
        history=history,
        n_init=n_init,
        n_steps=n_steps,
        bounds=[lo, hi],
    )


run = skill_run(
    {
        "gp_ei_1d": gp_ei_1d,
        "suggest": suggest,
    }
)

register_skill("bayesian_optimization", run)
