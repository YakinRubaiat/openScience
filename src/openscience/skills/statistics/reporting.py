"""statistical_reporting: APA-style formatting for tests, p-values, effect sizes."""

from __future__ import annotations

from typing import Any

import numpy as np

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run


def _fmt_p(p: float) -> str:
    """APA p-value: 'p = .023', 'p = .040', or 'p < .001'."""
    if p < 0.001:
        return "p < .001"
    return f"p = {p:.3f}".replace("0.", ".")


def _fmt_num(x: float, strip_leading_zero: bool = True) -> str:
    s = f"{x:.2f}"
    if strip_leading_zero and abs(x) < 1:
        s = s.replace("0.", ".") if x >= 0 else s.replace("-0.", "-.")
    return s


def _fmt_df(df: float) -> str:
    return str(int(df)) if float(df).is_integer() else f"{df:.1f}"


def apa_ttest(
    t_statistic: float | None = None,
    df: float | None = None,
    p_value: float | None = None,
    cohens_d: float | None = None,
    group1: Any | None = None,
    group2: Any | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Format a t-test as an APA string, e.g. 't(18) = 2.30, p = .034, d = 1.05'.

    Computes statistics from raw ``group1``/``group2`` arrays when given.
    """
    if group1 is not None and group2 is not None:
        from scipy import stats as _stats

        g1 = np.asarray(group1, dtype=float)
        g2 = np.asarray(group2, dtype=float)
        t_statistic, p_value = _stats.ttest_ind(g1, g2, equal_var=False)
        df = float(g1.size + g2.size - 2)
        s1, s2 = g1.std(ddof=1), g2.std(ddof=1)
        pooled = np.sqrt(((g1.size - 1) * s1**2 + (g2.size - 1) * s2**2) / max(g1.size + g2.size - 2, 1))
        cohens_d = float((g2.mean() - g1.mean()) / pooled) if pooled > 0 else 0.0

    if t_statistic is None or df is None or p_value is None:
        raise ValueError("Provide t_statistic/df/p_value or group1/group2 arrays")

    parts = [f"t({_fmt_df(df)}) = {_fmt_num(t_statistic)}",
             _fmt_p(p_value)]
    if cohens_d is not None:
        parts.append(f"d = {_fmt_num(cohens_d)}")
    apa = ", ".join(parts)
    return result(
        apa=apa,
        t_statistic=float(t_statistic),
        df=float(df),
        p_value=float(p_value),
        cohens_d=None if cohens_d is None else float(cohens_d),
        significant_at_005=bool(p_value < 0.05),
    )


def apa_anova(
    f_statistic: float | None = None,
    df_between: float | None = None,
    df_within: float | None = None,
    p_value: float | None = None,
    eta_squared: float | None = None,
    groups: Any | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Format one-way ANOVA as 'F(2, 27) = 4.56, p = .020, eta2 = .25'.

    Computes from a list of group arrays when ``groups`` is given.
    """
    if groups is not None:
        from scipy import stats as _stats

        arrs = [np.asarray(g, dtype=float) for g in groups]
        f_statistic, p_value = _stats.f_oneway(*arrs)
        n_total = sum(g.size for g in arrs)
        df_between = float(len(arrs) - 1)
        df_within = float(n_total - len(arrs))
        grand = np.concatenate(arrs).mean()
        ss_between = sum(g.size * (g.mean() - grand) ** 2 for g in arrs)
        ss_total = float(np.sum((np.concatenate(arrs) - grand) ** 2))
        eta_squared = float(ss_between / ss_total) if ss_total > 0 else 0.0

    if f_statistic is None or df_between is None or df_within is None or p_value is None:
        raise ValueError("Provide f_statistic/df_between/df_within/p_value or groups list")

    parts = [
        f"F({_fmt_df(df_between)}, {_fmt_df(df_within)}) = {_fmt_num(f_statistic)}",
        _fmt_p(p_value),
    ]
    if eta_squared is not None:
        parts.append(f"eta2 = {_fmt_num(eta_squared)}")
    apa = ", ".join(parts)
    return result(
        apa=apa,
        f_statistic=float(f_statistic),
        df_between=float(df_between),
        df_within=float(df_within),
        p_value=float(p_value),
        eta_squared=None if eta_squared is None else float(eta_squared),
        significant_at_005=bool(p_value < 0.05),
    )


def p_to_stars(p_value: float, **kwargs: Any) -> dict[str, Any]:
    """Significance stars: *** < .001, ** < .01, * < .05, ns otherwise."""
    if p_value < 0.001:
        stars = "***"
    elif p_value < 0.01:
        stars = "**"
    elif p_value < 0.05:
        stars = "*"
    else:
        stars = "ns"
    return result(p_value=float(p_value), stars=stars, significant_at_005=bool(p_value < 0.05))


def effect_size_label(d: float, metric: str = "cohens_d", **kwargs: Any) -> dict[str, Any]:
    """Label an effect size magnitude (Cohen's conventions).

    Cohen's d: small 0.2 / medium 0.5 / large 0.8.
    Pearson r: small 0.1 / medium 0.3 / large 0.5.
    eta^2:   small 0.01 / medium 0.06 / large 0.14.
    """
    thresholds = {
        "cohens_d": (0.2, 0.5, 0.8),
        "hedges_g": (0.2, 0.5, 0.8),
        "r": (0.1, 0.3, 0.5),
        "correlation": (0.1, 0.3, 0.5),
        "eta_squared": (0.01, 0.06, 0.14),
        "eta2": (0.01, 0.06, 0.14),
    }
    small, medium, large = thresholds.get(metric, (0.2, 0.5, 0.8))
    mag = abs(d)
    if mag >= large:
        label = "large"
    elif mag >= medium:
        label = "medium"
    elif mag >= small:
        label = "small"
    else:
        label = "negligible"
    return result(effect_size=float(d), metric=metric, magnitude=label,
                  thresholds={"small": small, "medium": medium, "large": large})


run = skill_run(
    {
        "apa_ttest": apa_ttest,
        "apa_anova": apa_anova,
        "p_to_stars": p_to_stars,
        "effect_size_label": effect_size_label,
    }
)

register_skill("statistical_reporting", run)
