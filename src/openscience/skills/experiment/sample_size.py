"""Sample size calculation skill: two means, two proportions, survival, correlation."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run


def _cohens_d(mean1: float, mean2: float, sd: float) -> float:
    if sd <= 0:
        raise ValueError("sd/pooled_sd must be positive")
    return abs(mean1 - mean2) / sd


def two_means(
    mean1: float | None = None,
    mean2: float | None = None,
    sd: float | None = None,
    pooled_sd: float | None = None,
    effect_size: float | None = None,
    alpha: float = 0.05,
    power: float = 0.8,
    ratio: float = 1.0,
    alternative: str = "two-sided",
    **kwargs: Any,
) -> dict[str, Any]:
    """Per-group sample size for comparing two means (two-sample t-test).

    Provide either (mean1, mean2, sd) or Cohen's ``effect_size`` directly.
    """
    from statsmodels.stats.power import TTestIndPower

    sd = sd if sd is not None else pooled_sd
    if effect_size is None:
        if mean1 is None or mean2 is None or sd is None:
            raise ValueError("provide effect_size or (mean1, mean2, sd)")
        effect_size = _cohens_d(mean1, mean2, sd)
    if effect_size == 0:
        raise ValueError("effect_size must be non-zero")

    n = TTestIndPower().solve_power(
        effect_size=effect_size, alpha=alpha, power=power, ratio=ratio,
        alternative=alternative,
    )
    n1 = int(math.ceil(n))
    return result(
        test="two-sample t-test",
        n_per_group=n1,
        n_group2=int(math.ceil(n * ratio)),
        n_total=n1 + int(math.ceil(n * ratio)),
        effect_size=float(effect_size),
        effect_metric="Cohen's d",
        alpha=float(alpha),
        power=float(power),
        ratio=float(ratio),
        alternative=alternative,
    )


def _cohens_h(p1: float, p2: float) -> float:
    return abs(2 * math.asin(math.sqrt(p1)) - 2 * math.asin(math.sqrt(p2)))


def two_proportions(
    p1: float | None = None,
    p2: float | None = None,
    effect_size: float | None = None,
    alpha: float = 0.05,
    power: float = 0.8,
    ratio: float = 1.0,
    alternative: str = "two-sided",
    **kwargs: Any,
) -> dict[str, Any]:
    """Per-group sample size for comparing two proportions (Cohen's h)."""
    from statsmodels.stats.power import TTestIndPower

    if effect_size is None:
        if p1 is None or p2 is None:
            raise ValueError("provide effect_size or (p1, p2)")
        if not (0 <= p1 <= 1 and 0 <= p2 <= 1):
            raise ValueError("p1 and p2 must be in [0, 1]")
        effect_size = _cohens_h(p1, p2)
    if effect_size == 0:
        raise ValueError("effect_size must be non-zero")

    n = TTestIndPower().solve_power(
        effect_size=effect_size, alpha=alpha, power=power, ratio=ratio,
        alternative=alternative,
    )
    n1 = int(math.ceil(n))
    return result(
        test="two-proportion z-test",
        n_per_group=n1,
        n_group2=int(math.ceil(n * ratio)),
        n_total=n1 + int(math.ceil(n * ratio)),
        effect_size=float(effect_size),
        effect_metric="Cohen's h",
        alpha=float(alpha),
        power=float(power),
        ratio=float(ratio),
        alternative=alternative,
    )


def survival(
    hr: float | None = None,
    hazard_ratio: float | None = None,
    p_event: float | None = None,
    event_prob: float | None = None,
    alpha: float = 0.05,
    power: float = 0.8,
    ratio: float = 1.0,
    alternative: str = "two-sided",
    **kwargs: Any,
) -> dict[str, Any]:
    """Sample size for comparing two survival curves (Freedman's formula).

    hr: hazard ratio (group2/group1). p_event: overall probability of the event
    during the study. Returns required number of events and total subjects.
    """
    from scipy.stats import norm

    hr = hr if hr is not None else hazard_ratio
    p_event = p_event if p_event is not None else event_prob
    if hr is None or hr <= 0 or hr == 1:
        raise ValueError("hr must be positive and != 1")
    if p_event is None or not (0 < p_event <= 1):
        raise ValueError("p_event must be in (0, 1]")
    if ratio <= 0:
        raise ValueError("ratio must be positive")

    z_alpha = norm.ppf(1 - alpha / 2) if alternative == "two-sided" else norm.ppf(1 - alpha)
    z_beta = norm.ppf(power)

    # Freedman: E = (z_a + z_b)^2 * (k*hr + 1)^2 / [ k * (hr - 1)^2 ], k = allocation ratio
    k = ratio
    n_events = ((z_alpha + z_beta) ** 2) * ((k * hr + 1) ** 2) / (k * (hr - 1) ** 2)
    n_total = n_events / p_event
    return result(
        test="log-rank survival comparison (Freedman)",
        n_events_required=int(math.ceil(n_events)),
        n_total=int(math.ceil(n_total)),
        n_group1=int(math.ceil(n_total / (1 + ratio))),
        n_group2=int(math.ceil(n_total * ratio / (1 + ratio))),
        hazard_ratio=float(hr),
        event_probability=float(p_event),
        alpha=float(alpha),
        power=float(power),
        ratio=float(ratio),
        alternative=alternative,
    )


def correlation(
    r: float | None = None,
    rho: float | None = None,
    alpha: float = 0.05,
    power: float = 0.8,
    alternative: str = "two-sided",
    **kwargs: Any,
) -> dict[str, Any]:
    """Sample size for detecting a significant Pearson correlation (Fisher z)."""
    from scipy.stats import norm

    r = r if r is not None else rho
    if r is None or not (-1 < r < 1) or r == 0:
        raise ValueError("r must be in (-1, 1) and non-zero")

    z_alpha = norm.ppf(1 - alpha / 2) if alternative == "two-sided" else norm.ppf(1 - alpha)
    z_beta = norm.ppf(power)
    # Fisher z-transform approximation: n = ((z_a + z_b) / atanh(r))^2 + 3
    n = ((z_alpha + z_beta) / math.atanh(abs(r))) ** 2 + 3
    return result(
        test="Pearson correlation (Fisher z)",
        n_total=int(math.ceil(n)),
        r=float(r),
        alpha=float(alpha),
        power=float(power),
        alternative=alternative,
    )


run = skill_run(
    {
        "two_means": two_means,
        "two_proportions": two_proportions,
        "survival": survival,
        "correlation": correlation,
    }
)

register_skill("sample_size_calc", run)
