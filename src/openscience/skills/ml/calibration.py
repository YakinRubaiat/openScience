"""Probability calibration skill: reliability bins, ECE, and Brier score.

Operations
----------
- ``reliability_bins`` — bin predicted probabilities against observed rates
- ``ece``              — expected calibration error
- ``brier``            — Brier score
"""

from __future__ import annotations

from typing import Any

import numpy as np

from openscience.skills import register_skill
from openscience.skills._common import skill_run, unwrap


def _get_probs(kw: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    prob = np.asarray(kw["probabilities"], dtype=float)
    truth = np.asarray(kw["y_true"]).astype(int)
    if prob.shape != truth.shape:
        raise ValueError("probabilities and y_true must have the same shape")
    if (prob < 0).any() or (prob > 1).any():
        raise ValueError("probabilities must lie in [0, 1]")
    return prob, truth


def reliability_bins(**kwargs: Any) -> dict[str, Any]:
    """Bin predicted probabilities and compare against observed event rates.

    Parameters: ``probabilities``, ``y_true``, ``n_bins`` (default 10).
    """
    kw = unwrap(kwargs)
    prob, truth = _get_probs(kw)
    n_bins = int(kw.get("n_bins", 10))
    n_bins = max(1, n_bins)

    edges = np.linspace(0.0, 1.0, n_bins + 1)
    edges[-1] = 1.0 + 1e-12  # include exactly 1.0 in the last bin

    bins: list[dict[str, Any]] = []
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        in_bin = (prob >= lo) & (prob < hi)
        n = int(in_bin.sum())
        if n == 0:
            bins.append(
                {
                    "bin_index": i,
                    "lower": float(lo),
                    "upper": float(min(hi, 1.0)),
                    "n": 0,
                    "mean_predicted": None,
                    "observed_frequency": None,
                }
            )
            continue
        mean_pred = float(prob[in_bin].mean())
        obs = float(truth[in_bin].mean())
        bins.append(
            {
                "bin_index": i,
                "lower": float(lo),
                "upper": float(min(hi, 1.0)),
                "n": n,
                "mean_predicted": mean_pred,
                "observed_frequency": obs,
                "gap": obs - mean_pred,
            }
        )
    return {"n": int(prob.shape[0]), "n_bins": n_bins, "bins": bins}


def ece(**kwargs: Any) -> dict[str, Any]:
    """Expected calibration error (weighted |observed - predicted|).

    Parameters: ``probabilities``, ``y_true``, ``n_bins`` (default 10).
    """
    kw = unwrap(kwargs)
    prob, truth = _get_probs(kw)
    n_bins = int(kw.get("n_bins", 10))
    n = prob.shape[0]

    edges = np.linspace(0.0, 1.0, n_bins + 1)
    edges[-1] = 1.0 + 1e-12

    total = 0.0
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        in_bin = (prob >= lo) & (prob < hi)
        n_bin = int(in_bin.sum())
        if n_bin == 0:
            continue
        gap = float(truth[in_bin].mean() - prob[in_bin].mean())
        total += (n_bin / n) * abs(gap)

    return {"n": int(n), "n_bins": n_bins, "ece": float(total)}


def brier(**kwargs: Any) -> dict[str, Any]:
    """Brier score: mean squared error of probabilistic predictions."""
    kw = unwrap(kwargs)
    prob, truth = _get_probs(kw)
    bs = float(np.mean((prob - truth) ** 2))
    base_rate = float(truth.mean())
    bs_reference = float(base_rate * (1.0 - base_rate))
    return {
        "n": int(prob.shape[0]),
        "brier_score": bs,
        "base_rate": base_rate,
        "reference_brier": bs_reference,
        "brier_skill_score": 1.0 - bs / bs_reference if bs_reference > 0 else None,
    }


run = skill_run(
    {
        "reliability_bins": reliability_bins,
        "ece": ece,
        "brier": brier,
    }
)

register_skill("calibration", run)
