#!/usr/bin/env python
"""Simulated clinical trial: full openScience agent pipeline with real skills.

Pipeline:
  power_analysis  -> sample size
  simulate        -> RCT data (continuous endpoint + time-to-event)
  statistical_modeler -> Welch t-test (primary) + Mann-Whitney (sensitivity)
  survival_analyzer   -> Kaplan-Meier + log-rank; Cox PH via lifelines skill
  matplotlib_stylist  -> 4 publication-quality figures
  abstract_writer     -> Results-section draft
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from real_skill_orchestrator import RealSkillOrchestrator

OUT = Path(__file__).resolve().parent
DATA, FIGS, RESULTS = OUT / "data", OUT / "figures", OUT / "results"
for d in (DATA, FIGS, RESULTS):
    d.mkdir(parents=True, exist_ok=True)

orch = RealSkillOrchestrator()
LOG: dict[str, dict] = {}
rng = np.random.default_rng(seed=42)  # reproducible


def log(step: str, result: dict):
    LOG[step] = result
    print(f"\n=== {step} ===")
    print(json.dumps(result, indent=2, default=str)[:900])


# ------------------------------------------------------------------ #
# STEP 3: power_analysis agent
# ------------------------------------------------------------------ #
pa_result = orch.execute_agent(
    "power_analysis",
    {"effect_size": 0.5, "alpha": 0.05, "power": 0.8},
    {},
).data
pa = pa_result["data"] if "data" in pa_result else pa_result
log("power_analysis", pa)
N_PER_GROUP = pa["n_per_group"]  # 64

# ------------------------------------------------------------------ #
# STEP 4: simulate the trial
# ------------------------------------------------------------------ #
# Continuous primary endpoint: e.g. reduction in symptom score (higher = better)
# Control ~ N(10, 3); treatment uplift chosen so Cohen's d = 0.5 -> +1.5 units
control = rng.normal(loc=10.0, scale=3.0, size=N_PER_GROUP)
treatment = rng.normal(loc=11.5, scale=3.0, size=N_PER_GROUP)

# Time-to-event: days-to-relapse, treatment halves the hazard (HR=0.5)
# ~5% loss to follow-up (censoring) per group
lam_c, lam_t = 1 / 60.0, 0.5 / 60.0  # exponential rates
time_c = rng.exponential(1 / lam_c, N_PER_GROUP)
time_t = rng.exponential(1 / lam_t, N_PER_GROUP)
event_c = (rng.random(N_PER_GROUP) > 0.05).astype(int)
event_t = (rng.random(N_PER_GROUP) > 0.05).astype(int)

df = pd.DataFrame(
    {
        "subject_id": [f"C{i:03d}" for i in range(N_PER_GROUP)]
        + [f"T{i:03d}" for i in range(N_PER_GROUP)],
        "arm": ["control"] * N_PER_GROUP + ["treatment"] * N_PER_GROUP,
        "endpoint": np.concatenate([control, treatment]),
        "time": np.concatenate([time_c, time_t]),
        "event": np.concatenate([event_c, event_t]),
    }
)
df.to_csv(DATA / "trial_data.csv", index=False)
log(
    "simulation",
    {
        "n_per_group": N_PER_GROUP,
        "control_mean": float(control.mean()),
        "treatment_mean": float(treatment.mean()),
        "events_control": int(event_c.sum()),
        "events_treatment": int(event_t.sum()),
        "csv": str(DATA / "trial_data.csv"),
    },
)

# ------------------------------------------------------------------ #
# STEP 5: statistical_modeler agent — primary + sensitivity analyses
# ------------------------------------------------------------------ #
ttest_res = orch.execute_agent(
    "statistical_modeler",
    {"group1": control.tolist(), "group2": treatment.tolist(), "equal_var": False},
    {},
).data
ttest = ttest_res["data"] if "data" in ttest_res else ttest_res
log("statistical_modeler_fresh", ttest)

# Sensitivity: Mann-Whitney via scipy skill directly through orchestrator
mw = orch.execute_skill(
    "scipy_stats", "mannwhitney", group1=control.tolist(), group2=treatment.tolist()
)["data"]
log("mannwhitney_sensitivity", mw)

# Normality check
shapiro_c = orch.execute_skill("scipy_stats", "shapiro", data=control.tolist())["data"]
shapiro_t = orch.execute_skill("scipy_stats", "shapiro", data=treatment.tolist())["data"]

# ------------------------------------------------------------------ #
# STEP 6: survival_analyzer agent — KM + log-rank, then Cox PH
# ------------------------------------------------------------------ #
groups = np.array([0] * N_PER_GROUP + [1] * N_PER_GROUP)  # 0=ctrl 1=treat
sv_res = orch.execute_agent(
    "survival_analyzer",
    {
        "durations": df.time.tolist(),
        "events": df.event.tolist(),
        "groups": groups.tolist(),
    },
    {},
).data
sv = sv_res["data"] if "data" in sv_res else sv_res
log("survival_analyzer", {k: v for k, v in sv.items() if k != "groups"})

cox = orch.execute_skill(
    "lifelines",
    "cox",
    dataframe={
        "time": df.time.tolist(),
        "event": df.event.tolist(),
        "treatment": groups.tolist(),
        "endpoint": df.endpoint.tolist(),  # baseline severity as covariate
    },
    duration_col="time",
    event_col="event",
)["data"]
log("cox_ph", cox)

# ------------------------------------------------------------------ #
# STEP 7: matplotlib_stylist agent — 4 figures
# ------------------------------------------------------------------ #
figure_files: dict[str, str] = {}


def style_save(fig, fname: str) -> str:
    path = str(FIGS / fname)
    res = orch.execute_agent("matplotlib_stylist", {"figure": fig, "style": "nature"}, {}).data
    orch.execute_skill("matplotlib", "apply_style", figure=fig, style="nature", save_path=path)
    plt.close(fig)
    return res["data"]["saved_to"] if isinstance(res, dict) and "data" in res else path


# Fig 1: power curve
fig, ax = plt.subplots(figsize=(3.5, 2.6))
curve = pa["power_curve"]
ax.plot([p["n_per_group"] for p in curve], [p["power"] for p in curve], "o-", color="#1f77b4")
ax.axhline(0.8, ls="--", lw=0.8, color="grey")
ax.axvline(N_PER_GROUP, ls=":", lw=0.8, color="red")
ax.set_xlabel("Sample size per group")
ax.set_ylabel("Statistical power")
ax.set_title("A priori power analysis (d = 0.5, α = 0.05)")
figure_files["power_curve"] = style_save(fig, "fig1_power_curve.png")

# Fig 2: primary endpoint distributions
fig, ax = plt.subplots(figsize=(3.5, 2.6))
ax.boxplot(
    [control, treatment],
    tick_labels=["Control", "Treatment"],
    widths=0.5,
    patch_artist=True,
    boxprops=dict(facecolor="#aec7e8"),
    medianprops=dict(color="black"),
    showmeans=True,
    meanprops=dict(marker="D", markerfacecolor="red", markersize=4),
)
for i, vals in enumerate([control, treatment]):
    ax.scatter(rng.normal(i + 1, 0.04, len(vals)), vals, s=4, alpha=0.35, color="#333")
ax.set_ylabel("Symptom-score change")
ax.set_title(f"Primary endpoint (p = {ttest['p_value']:.4f}, d = {ttest['cohens_d']:.2f})")
figure_files["endpoint"] = style_save(fig, "fig2_primary_endpoint.png")

# Fig 3: Kaplan-Meier curves
fig, ax = plt.subplots(figsize=(3.5, 2.6))
color_map = {"0": "#9467bd", "1": "#2ca02c"}
for gname, gdata in sv["groups"].items():
    ax.step(
        gdata["timeline"],
        gdata["survival"],
        where="post",
        label=("Control" if gname == "0" else "Treatment"),
        color=color_map[gname],
    )
ax.set_xlabel("Time (days)")
ax.set_ylabel("Event-free probability")
ax.set_ylim(0, 1.02)
ax.legend(loc="lower left")
lr = sv["logrank"]
ax.set_title(f"Kaplan–Meier (log-rank p = {lr['p_value']:.4f})")
figure_files["km"] = style_save(fig, "fig3_kaplan_meier.png")

# Fig 4: Cox PH forest-style HR plot
fig, ax = plt.subplots(figsize=(3.5, 1.9))
covs = cox["covariates"]
names = list(covs)
hrs = [covs[n]["hazard_ratio"] for n in names]
los = [covs[n]["hr_ci95_lower"] for n in names]
his = [covs[n]["hr_ci95_upper"] for n in names]
ys = np.arange(len(names))
ax.errorbar(hrs, ys, xerr=[np.array(hrs) - np.array(los), np.array(his) - np.array(hrs)],
            fmt="o", color="#d62728", ecolor="#d62728", capsize=3)
ax.axvline(1.0, ls="--", lw=0.8, color="grey")
ax.set_yticks(ys, names)
ax.set_xscale("log")
ax.set_xlabel("Hazard ratio (log scale)")
ax.set_title("Cox proportional-hazards model")
figure_files["cox"] = style_save(fig, "fig4_cox_forest.png")

# ------------------------------------------------------------------ #
# STEP 8: abstract_writer — draft Results section
# ------------------------------------------------------------------ #
results_bundle = {
    "power_analysis": pa,
    "primary_endpoint": ttest,
    "sensitivity_analysis": mw,
    "survival": sv,
    "cox_ph": cox,
}
draft = orch.execute_skill("scientific_writing", "write_results", results=results_bundle)["data"]
wr_res = orch.execute_agent(
    "abstract_writer",
    {"paper_content": draft["results_text"], "target_journal": "general", "word_limit": 300},
    {},
).data
log("results_writer", {"word_count": draft["word_count"]})
(RESULTS / "results_section.md").write_text(draft["results_text"] + "\n")

# ------------------------------------------------------------------ #
# Save machine-readable results
# ------------------------------------------------------------------ #
summary = {
    "power_analysis": pa,
    "primary_endpoint": ttest,
    "sensitivity_analysis": mw,
    "normality": {"control": shapiro_c, "treatment": shapiro_t},
    "survival": {k: v for k, v in sv.items() if k != "groups"},
    "cox_ph": cox,
    "figures": figure_files,
}
(RESULTS / "analysis_summary.json").write_text(json.dumps(summary, indent=2, default=str))
print("\nSaved:", RESULTS / "analysis_summary.json")
print("Figures:", *figure_files.values(), sep="\n  ")
