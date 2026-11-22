"""Power analysis skill: t-test and proportion power via statsmodels."""

from __future__ import annotations

from typing import Any

import numpy as np

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run


def ttest_power(
    effect_size: float | None = None,
    nobs1: float | None = None,
    alpha: float = 0.05,
    power: float | None = None,
    ratio: float = 1.0,
    alternative: str = "two-sided",
    **kwargs: Any,
) -> dict[str, Any]:
    """Solve for the missing one of (effect_size, nobs1, power) in a two-sample t-test."""
    from statsmodels.stats.power import TTestIndPower

    solver = TTestIndPower()
    val = solver.solve_power(
        effect_size=effect_size,
        nobs1=nobs1,
        alpha=alpha,
        power=power,
        ratio=ratio,
        alternative=alternative,
    )
    solved_for = (
        "effect_size" if effect_size is None else ("nobs1" if nobs1 is None else "power")
    )
    return result(
        test="two-sample t-test power",
        solved_for=solved_for,
        value=float(val),
        effect_size=float(val if effect_size is None else effect_size),
        nobs1=float(val if nobs1 is None else nobs1),
        power=float(val if power is None else power),
        alpha=float(alpha),
        ratio=float(ratio),
        alternative=alternative,
    )


def sample_size(
    effect_size: float,
    alpha: float = 0.05,
    power: float = 0.8,
    ratio: float = 1.0,
    alternative: str = "two-sided",
    **kwargs: Any,
) -> dict[str, Any]:
    """Required sample size per group for a two-sample t-test."""
    from statsmodels.stats.power import TTestIndPower

    n = TTestIndPower().solve_power(
        effect_size=effect_size, alpha=alpha, power=power, ratio=ratio, alternative=alternative
    )
    return result(
        test="two-sample t-test sample size",
        effect_size=float(effect_size),
        alpha=float(alpha),
        power=float(power),
        ratio=float(ratio),
        alternative=alternative,
        n_per_group=int(np.ceil(n)),
        n_total=int(np.ceil(n) * (1 + ratio)),
    )


def power_curve(
    effect_size: float,
    n_range: Any | None = None,
    alpha: float = 0.05,
    ratio: float = 1.0,
    alternative: str = "two-sided",
    **kwargs: Any,
) -> dict[str, Any]:
    """Power over a grid of per-group sample sizes; returns a list of dicts."""
    from statsmodels.stats.power import TTestIndPower

    solver = TTestIndPower()
    if n_range is None:
        # center the grid on the n required for 80% power
        n_req = solver.solve_power(
            effect_size=effect_size, alpha=alpha, power=0.8, ratio=ratio,
            alternative=alternative,
        )
        n_grid = np.unique(
            np.clip(np.round(np.linspace(n_req * 0.25, n_req * 1.75, 9)).astype(int), 2, None)
        )
    else:
        n_grid = np.unique(np.asarray(n_range, dtype=int))

    curve = [
        {
            "n_per_group": int(n),
            "power": float(
                solver.power(
                    effect_size=effect_size, nobs1=int(n), alpha=alpha,
                    ratio=ratio, alternative=alternative,
                )
            ),
        }
        for n in n_grid
    ]
    return result(
        test="two-sample t-test power curve",
        effect_size=float(effect_size),
        alpha=float(alpha),
        ratio=float(ratio),
        curve=curve,
    )


def proportion_power(
    effect_size: float | None = None,
    nobs1: float | None = None,
    power: float | None = None,
    alpha: float = 0.05,
    ratio: float = 1.0,
    alternative: str = "two-sided",
    **kwargs: Any,
) -> dict[str, Any]:
    """Power/sample-size for a two-proportion test (Cohen's h effect size)."""
    from statsmodels.stats.power import TTestIndPower

    solver = TTestIndPower()
    val = solver.solve_power(
        effect_size=effect_size, nobs1=nobs1, alpha=alpha, power=power,
        ratio=ratio, alternative=alternative,
    )
    solved_for = (
        "effect_size" if effect_size is None else ("nobs1" if nobs1 is None else "power")
    )
    return result(
        test="two-proportion test power",
        effect_metric="Cohen's h",
        solved_for=solved_for,
        value=float(val),
        effect_size=float(val if effect_size is None else effect_size),
        nobs1=float(val if nobs1 is None else nobs1),
        power=float(val if power is None else power),
        alpha=float(alpha),
        alternative=alternative,
    )


run = skill_run(
    {
        "ttest_power": ttest_power,
        "sample_size": sample_size,
        "power_curve": power_curve,
        "proportion_power": proportion_power,
    }
)

register_skill("power_analysis", run)
