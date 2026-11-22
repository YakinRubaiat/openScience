# Experiment: Simulated Clinical Trial with openScience

**Date:** 2026-11-22
**Goal:** Determine whether openScience can actually help design and analyze a clinical trial.

---

## Step 1: Check statistics skills in `src/openscience/skills/statistics/`

### What I tried
- Listed `src/openscience/skills/statistics/` → **empty directory** (0 files).
- Listed all skill category dirs: `bioinformatics/`, `cheminformatics/`, `general/`, `statistics/`, `visualization/`, `writing/` — **all empty**.
- Checked agents: 111 agents load fine. The 5 target agents exist:
  - `power_analysis` (experiment), `statistical_modeler` (analysis), `survival_analyzer` (analysis),
    `matplotlib_stylist` (visualization), `abstract_writer` (writing).
- Read `AgentOrchestrator.execute_skill()` (core/orchestrator.py:164-185).

### Finding
**The skill system is a stub.** `execute_skill()` returns `{"skill": name, "operation": op, "status": "ok", "data": kwargs}` —
it echoes back its inputs without computing anything. The agents "execute" but produce fabricated
passthrough results. This matches `tests/integration/EXPERIMENT_03_AGENTS.md` where
`power_analysis` returned `{"effect_size": 0.5, "alpha": 0.05, "power": 0.8}` — i.e., exactly the
inputs, no sample size was computed.

### Environment issues
- `statsmodels` and `lifelines` were NOT installed (agents declare them as required skills).
- Installed into `.venv`: `statsmodels-0.15.0`, `lifelines-0.30.3`.
- **Side effect:** pip downgraded `pandas 3.1.1 → 2.3.3` (statsmodels pin). Re-verified all 111 agents still load. ✅

### What I had to implement
1. Real skill modules in `src/openscience/skills/statistics/`:
   - `statsmodels_skill.py` — power analysis, t-test, Mann-Whitney, OLS regression
   - `scipy_stats_skill.py` — descriptive stats, t-tests, chi-square
   - `lifelines_skill.py` — Kaplan-Meier, log-rank test, Cox PH
   - `matplotlib_skill.py` — publication styling + figure save
   - `scientific_writing_skill.py` — results-section drafting (template-based)
2. `RealSkillOrchestrator` that binds these modules to skill names and dispatches operations.

(Details in the following steps.)
