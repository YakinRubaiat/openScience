"""Template-based scientific-writing skill (deterministic, no LLM).

Drafts a Results/abstract-style section from structured statistical results.
Honours a word limit with a simple truncation + sentence-boundary trim.
"""

from __future__ import annotations

import re
from typing import Any


def run(operation: str, **kwargs: Any) -> dict[str, Any]:
    if operation == "write_abstract":
        return write_abstract(**kwargs)
    if operation == "write_results":
        return write_results(**kwargs)
    raise ValueError(f"Unknown scientific_writing operation: {operation}")


def _fmt_p(p: float | None) -> str:
    if p is None:
        return "NA"
    return "< 0.001" if p < 0.001 else f"= {p:.3f}"


def write_results(results: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Compose a Results paragraph from power/t-test/survival result dicts."""
    sentences: list[str] = []

    pa = results.get("power_analysis")
    if pa:
        sentences.append(
            f"A priori power analysis indicated that {pa['n_per_group']} participants per group "
            f"(N = {pa['n_total']} total) were required to detect a medium effect "
            f"(Cohen's d = {pa['effect_size']}) with {int(pa['power_target']*100)}% power at "
            f"α = {pa['alpha']} (two-sided {pa['test']})."
        )

    tt = results.get("primary_endpoint")
    if tt:
        sentences.append(
            f"The primary endpoint differed significantly between treatment "
            f"(mean = {tt['mean_group2']:.2f}, SD = {tt['sd_group2']:.2f}, n = {tt['n2']}) and "
            f"control (mean = {tt['mean_group1']:.2f}, SD = {tt['sd_group1']:.2f}, n = {tt['n1']}) groups "
            f"(mean difference = {tt['mean_diff']:.2f}, 95% CI "
            f"[{tt['mean_diff_ci95'][0]:.2f}, {tt['mean_diff_ci95'][1]:.2f}]; "
            f"{tt['test']}: t({tt['df']:.1f}) = {tt['t_statistic']:.2f}, p {_fmt_p(tt['p_value'])}; "
            f"Cohen's d = {tt['cohens_d']:.2f})."
        )

    mw = results.get("sensitivity_analysis")
    if mw:
        sentences.append(
            f"A non-parametric sensitivity analysis ({mw['test']}) confirmed the primary result "
            f"(U = {mw['u_statistic']:.1f}, p {_fmt_p(mw['p_value'])}; "
            f"rank-biserial r = {mw['rank_biserial_r']:.2f})."
        )

    sv = results.get("survival")
    if sv and "logrank" in sv:
        lr = sv["logrank"]
        groups = sv["groups"]
        gnames = list(groups)
        label = {"0": "control", "1": "treatment"}
        med = ", ".join(
            (
                f"{label.get(name, name)}: {groups[name]['median_survival']:.1f} time units"
                if groups[name]["median_survival"] is not None
                else f"{label.get(name, name)}: not reached"
            )
            for name in gnames
        )
        sentences.append(
            f"Time-to-event analysis showed a significant difference between arms "
            f"(log-rank χ² = {lr['statistic']:.2f}, p {_fmt_p(lr['p_value'])}; median survival — {med})."
        )

    cox = results.get("cox_ph")
    if cox and "treatment" in cox.get("covariates", {}):
        c = cox["covariates"]["treatment"]
        sentences.append(
            f"In a Cox proportional-hazards model (concordance = {cox['concordance']:.2f}), "
            f"treatment was associated with a hazard ratio of {c['hazard_ratio']:.2f} "
            f"(95% CI {c['hr_ci95_lower']:.2f}–{c['hr_ci95_upper']:.2f}, p {_fmt_p(c['p_value'])})."
        )

    text = " ".join(sentences)
    return {"results_text": text, "word_count": len(text.split()), "sentences": len(sentences)}


def write_abstract(
    content: str = "", journal: str = "general", word_limit: int = 250, **kwargs: Any
) -> dict[str, Any]:
    """Wrap/trim provided prose into an abstract-conformant draft."""
    text = content or kwargs.get("results", {}).get("results_text", "")
    words = text.split()
    truncated = False
    if len(words) > word_limit:
        cut = " ".join(words[:word_limit])
        # Trim to the last sentence boundary to avoid dangling fragments.
        m = list(re.finditer(r"[.!?]", cut))
        text = cut[: m[-1].end()] if m else cut
        truncated = True
    return {
        "abstract_draft": text,
        "target_journal": journal,
        "word_count": len(text.split()),
        "word_limit": word_limit,
        "truncated_to_limit": truncated,
    }
