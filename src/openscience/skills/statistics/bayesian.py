"""Conjugate Bayesian inference: beta-binomial and normal-normal updates."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import stats

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run


def beta_binomial(
    successes: int,
    failures: int = 0,
    alpha_prior: float = 1.0,
    beta_prior: float = 1.0,
    ci_mass: float = 0.89,
    **kwargs: Any,
) -> dict[str, Any]:
    """Beta-binomial conjugate update.

    Posterior: Beta(alpha_prior + successes, beta_prior + failures).
    HDPI approximated via the beta distribution's quantile function (ppf).
    """
    a = alpha_prior + successes
    b = beta_prior + failures
    lo = (1 - ci_mass) / 2
    lower, upper = stats.beta.ppf([lo, 1 - lo], a, b)
    posterior_mean = a / (a + b)
    return result(
        model="beta_binomial",
        posterior_alpha=float(a),
        posterior_beta=float(b),
        posterior_mean=float(posterior_mean),
        posterior_mode=float((a - 1) / (a + b - 2)) if a > 1 and b > 1 else None,
        posterior_var=float(a * b / ((a + b) ** 2 * (a + b + 1))),
        hdpi_mass=float(ci_mass),
        hdpi_lower=float(lower),
        hdpi_upper=float(upper),
        prior_mean=float(alpha_prior / (alpha_prior + beta_prior)),
    )


def normal_normal(
    data_mean: float,
    data_sd: float,
    n: int,
    prior_mean: float = 0.0,
    prior_sd: float = 1.0,
    ci_mass: float = 0.89,
    **kwargs: Any,
) -> dict[str, Any]:
    """Normal-normal conjugate update for a known data_sd."""
    prior_prec = 1.0 / prior_sd**2
    data_prec = n / data_sd**2
    post_prec = prior_prec + data_prec
    post_mean = (prior_mean * prior_prec + data_mean * data_prec) / post_prec
    post_sd = 1.0 / np.sqrt(post_prec)
    lo = (1 - ci_mass) / 2
    lower, upper = stats.norm.ppf([lo, 1 - lo], loc=post_mean, scale=post_sd)
    return result(
        model="normal_normal",
        posterior_mean=float(post_mean),
        posterior_sd=float(post_sd),
        hdpi_mass=float(ci_mass),
        hdpi_lower=float(lower),
        hdpi_upper=float(upper),
        prior_mean=float(prior_mean),
        prior_sd=float(prior_sd),
        data_mean=float(data_mean),
        n=int(n),
    )


def summary(
    posterior_mean: float | None = None,
    posterior_sd: float | None = None,
    ci_mass: float = 0.89,
    hdpi_lower: float | None = None,
    hdpi_upper: float | None = None,
    alpha: float | None = None,
    beta: float | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Summarize a posterior: mean, HDPI and P(parameter > threshold)."""
    threshold = float(kwargs.get("threshold", 0.0))
    mass = float(ci_mass)
    lo_q = (1 - mass) / 2

    if alpha is not None and beta is not None:
        dist = stats.beta(alpha, beta)
        mean = float(alpha / (alpha + beta))
    elif posterior_mean is not None and posterior_sd is not None:
        dist = stats.norm(loc=posterior_mean, scale=posterior_sd)
        mean = float(posterior_mean)
    elif posterior_mean is not None:
        dist = None
        mean = float(posterior_mean)
    else:
        raise ValueError("Provide alpha/beta or posterior_mean")

    if dist is not None:
        lower, upper = dist.ppf([lo_q, 1 - lo_q])
        p_gt = float(1 - dist.cdf(threshold))
    else:
        lower = float(hdpi_lower) if hdpi_lower is not None else None
        upper = float(hdpi_upper) if hdpi_upper is not None else None
        p_gt = None

    return result(
        posterior_mean=mean,
        hdpi_mass=mass,
        hdpi_lower=lower,
        hdpi_upper=upper,
        threshold=threshold,
        p_greater_than_threshold=p_gt,
    )


run = skill_run(
    {
        "beta_binomial": beta_binomial,
        "normal_normal": normal_normal,
        "summary": summary,
    }
)

register_skill("bayesian_inference", run)
