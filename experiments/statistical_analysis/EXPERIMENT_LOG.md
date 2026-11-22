# Experiment: Simulated Clinical Trial with openScience

**Date:** 2026-11-22
**Goal:** Determine whether openScience can actually help design and analyze a clinical trial
(power → simulate → test → survival → figures → results prose) end-to-end.

**Verdict: only with substantial glue code. The agent framework works, but the skill layer is
a passthrough stub — out of the box, agents return their inputs, not results.**

---

## Step 1 — Do statistics skills exist?

**Tried:** listed `src/openscience/skills/statistics/` and all skill dirs.

**Finding:** every skills directory is **empty**. No `__init__.py`, no modules — for any
category (statistics, visualization, writing, bioinformatics, cheminformatics, general).
Meanwhile 111 agents load fine and `AgentOrchestrator.execute_skill()` (core/orchestrator.py:164-185)
just returns `{"skill": name, "operation": op, "status": "ok", "data": kwargs}` — it **echoes its
inputs**. Demonstrated: `power_analysis` with `{effect_size:0.5, alpha:0.05, power:0.8}` returned
exactly that dict with **no sample size computed**. This matches `EXPERIMENT_3_RESULTS.md`, which
flagged a "PASS" for `power_analysis` while its recorded output was clearly the input passthrough.

**Environment errors:** `statsmodels` and `lifelines` (declared as `required_skills` by the agents)
were not installed. Installed into `.venv`: statsmodels 0.15.0, lifelines 0.30.3.
Side effect: pip downgraded **pandas 3.1.1 → 2.3.3** (statsmodels pin); all 111 agents still load.

---

## Step 2 — Implement the missing skills

Created real, scipy/statsmodels/lifelines/matplotlib-backed skill modules, each exposing
`run(operation, **kwargs)`:

| File | Operations |
|---|---|
| `skills/statistics/statsmodels_skill.py` | `power_analysis` (TTestIndPower + power curve), `ttest` (Welch/Student via CompareMeans, Cohen's d, Hedges' g, CI), `ols` |
| `skills/statistics/scipy_stats_skill.py` | `describe`, `mannwhitney` (+rank-biserial r), `shapiro` |
| `skills/statistics/lifelines_skill.py` | `kaplan_meier` (+log-rank), `cox` (Cox PH w/ HR CIs) |
| `skills/visualization/matplotlib_skill.py` | `apply_style` (Nature-ish rcParams, 300-DPI save) |
| `skills/writing/scientific_writing_skill.py` | `write_results` (template prose), `write_abstract` (word-limit trim) |

Plus `RealSkillOrchestrator` (`real_skill_orchestrator.py`), a subclass binding skill names to
modules, with an operation-alias table — because agents request operations their module doesn't own
(`statistical_modeler` calls `statsmodels.run` ⇒ mapped to `ttest`; `lifelines.run` ⇒ `kaplan_meier`;
unknown skills fall back to the stub so nothing crashes).

**Bugs found & fixed during implementation:**
1. `matplotlib >=3.9` removed the `labels=` kwarg from `Axes.boxplot` → `TypeError`. Fixed with `tick_labels=`.
2. Sign mismatch in my `ttest`: `CompareMeans(d1,d2).tconfint_diff()` is the CI for d1−d2 while
   `mean_diff` was computed as m2−m1, giving an inconsistent CI `[-1.85, -0.18]` for a positive diff.
   Swapped to `CompareMeans(d2, d1)` → CI `[0.18, 1.85]`. (Catches why blind passthrough results can
   hide real numerical bugs.)

---

## Step 3 — Power analysis (medium effect, d=0.5, power=0.8, α=0.05)

**Stub result:** `{'effect_size': 0.5, 'alpha': 0.05, 'power': 0.8}` — no answer. ❌

**Real-skill result (statsmodels `TTestIndPower`):**

| Parameter | Value |
|---|---|
| n per group | **64** (63.03 → ceil) |
| total N | **128** |
| test | two-sample t-test, two-sided |
| power curve | n=57 → 0.754 · n=64 → ~0.80 · n=71 → 0.841 |

✅ Matches the known textbook answer for d=0.5 / power 0.8 / α 0.05.

---

## Step 4 — Simulated trial (reproducible, seed=42)

- Primary endpoint (symptom-score change): control ~ N(10, 3), treatment ~ N(11.5, 3) (planned d=0.5).
- Time-to-event (days-to-relapse): exponential, treatment hazard = 0.5 × control; ~5% censored/arm.
- Saved: `data/trial_data.csv` (128 rows: subject_id, arm, endpoint, time, event).

Observed: control mean 10.12, treatment mean 11.14; events 61/64 (ctrl), 64/64 (treat).

---

## Step 5 — `statistical_modeler` agent

| Analysis | Result |
|---|---|
| **Welch t-test (primary)** | diff = **1.02** (95% CI 0.18–1.85), t(126.0) = 2.40, **p = 0.018**, Cohen's d = 0.42, Hedges' g = 0.42 |
| Mann–Whitney (sensitivity) | U = 1583, **p = 0.027**, rank-biserial r = 0.23 |
| Shapiro–Wilk (normality) | control p = 0.91, treatment p = 0.54 → normality holds, t-test appropriate |

✅ Primary + non-parametric sensitivity agree; observed d (0.42) close to simulated 0.5.

---

## Step 6 — `survival_analyzer` agent + Cox PH

| Analysis | Result |
|---|---|
| Kaplan–Meier medians | control **48.5** days · treatment **91.6** days |
| Log-rank | χ² = 13.96, **p = 0.00019** |
| Cox PH (treatment, baseline endpoint) | HR = **0.48** (95% CI 0.33–0.72, **p = 0.00033**); baseline endpoint NS (p = 0.76); concordance 0.58 |

✅ Recovers the simulated HR ≈ 0.5.

---

## Step 7 — `matplotlib_stylist` agent (Nature-style, 300 DPI)

`figures/fig1_power_curve.png`, `fig2_primary_endpoint.png`, `fig3_kaplan_meier.png`,
`fig4_cox_forest.png` — all clean, no top/right spines, out-ticks, specified colours. ✅

---

## Step 8 — `abstract_writer` / results drafting

`results/results_section.md` (152 words), e.g.:

> "The primary endpoint differed significantly between treatment (mean = 11.14, SD = 2.40, n = 64)
> and control (mean = 10.12, SD = 2.39, n = 64) groups (mean difference = 1.02, 95% CI [0.18, 1.85];
> Welch t-test: t(126.0) = 2.40, p = 0.018; Cohen's d = 0.42)… treatment was associated with a hazard
> ratio of 0.48 (95% CI 0.33–0.72, p < 0.001)."

Template-based (no LLM) — accurate but purely mechanical; no framing/interpretation.

---

## Can openScience actually help design & analyze a clinical trial?

**Partially.** The agent framework (metadata, registry, `BaseAgent.run_skill`, orchestrator
dispatch) is sound and the 111 agents load and execute — so the *plumbing* works. But:

### What's missing
1. **All skill implementations.** `skills/` is empty across the board; `execute_skill` is an echo
   stub. Nothing computes anything out of the box — the single biggest gap.
2. **Declared dependencies aren't installed** (`statsmodels`, `lifelines` absent; installing them
   silently downgraded pandas, risking breakage elsewhere).
3. **Operation-name mismatch** between agents and any real skill API — agents call
   `skill.run("run", parameters={...})`; skills need to know their own operation names, so an alias
   layer is required.
4. **Result-shape contract.** Agents just `format_result(run_skill(...))`; there is no typed schema,
   so chaining is ad-hoc. The abstract writer can't ingest statistical results natively — I had to
   add a `write_results` skill and hand-bundle the outputs.
5. **No real tests of substance.** Experiment-3 "PASS"ed agents that returned their own inputs.
6. Writing skill is template-only; no LLM → no genuine abstract drafting.
7. Missing for a *real* trial: randomization/blinding execution (agent stubs exist, no impl),
   multiple-comparison control, assumption-diagnostics reports, ITT/PP analysis, CONSORT outputs.

### What I'd keep
- `RealSkillOrchestrator` binding pattern (works, minimal intrusion).
- Skill modules with a uniform `run(operation, **kwargs)` entry point.
- The output artifacts: `data/trial_data.csv`, `results/analysis_summary.json`,
  `results/results_section.md`, 4 figures — a genuinely usable, reproducible trial-analysis skeleton.

**Bottom line:** openScience is a workable *scaffold*, but today it needs real skills wired in
before it does any real statistics. With those added, the pipeline ran end-to-end and produced
correct, publication-ready trial analyses.
