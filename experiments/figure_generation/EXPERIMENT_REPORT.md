# openScience Figure-Generation Experiment

**Date:** 2026-11-22
**Working directory:** `/Users/srubaiat/openScience`
**Output:** `experiments/figure_generation/`
**Run script:** `run_figure_experiment.py`

## Goal

Test whether the openScience agent-orchestrator architecture can actually
produce a publication-quality multi-panel scientific figure from scratch,
including:
1. Generating synthetic multi-omics data.
2. Driving the existing visualization *agents* (`publication_formatter`,
   `layout_composer`, `color_palette_designer`, `matplotlib_stylist`,
   `seaborn_stylist`).
3. Wiring up the (previously missing) *skills* those agents call.
4. Emitting PDF + PNG + SVG.

## What existed vs. what had to be built

| Component | State when experiment started |
| --- | --- |
| `src/openscience/agents/visualization/*.py` | **Existed** as stubs (16 agent classes) but they just call `run_skill(skill_name, operation, …)` — they don't make figures themselves. |
| `src/openscience/skills/visualization/` | **Empty directory.** The orchestrator's `execute_skill` was a stub that just echoed kwargs back. |
| `core/orchestrator.AgentOrchestrator.execute_skill` | **Stub implementation** returning `{"skill": name, "operation": op, "status": "ok", "data": kwargs}`. |
| Synthetic multi-omics data generator | Did not exist. |
| End-to-end experiment runner | Did not exist. |

So the figure-generation capability had to be **built from scratch** as real
Python skills and then **bound to the orchestrator** by subclassing
`AgentOrchestrator`.

## Step-by-step log

### 1. Skill implementation

Created four new skills under `src/openscience/skills/visualization/`:

- **`matplotlib_skill.py`** — `render` operation supports
  `volcano`, `heatmap`, `kaplan_meier`, `correlation_matrix`, `box`.
  `apply_style` re-styles an existing figure. Also defines the Nature rcParams
  and `_save_all` (PDF/PNG/SVG triple output).
- **`matplotlib_gridspec.py`** — composes a list of panel specs into a
  2×2 GridSpec multi-panel figure with auto panel letters (a, b, c, d).
- **`colorbrewer.py`** — returns Okabe-Ito / ColorBrewer palettes; rough
  Vienot-CVD simulation that reports min pairwise distance between simulated
  colours as an accessibility diagnostic.
- **`seaborn_skill.py`** — boxplot/violin/strip/swarm/regplot/clustermap
  wrappers with Nature-style rcParams layered on top.

Surprise: another concurrent agent/process started dumping partial stub
implementations into `src/openscience/skills/` (statistics/, general/, etc.)
mid-experiment. One of them overwrote my `matplotlib_skill.py` with a smaller
version that only handled `apply_style`. I had to rewrite that file (this one
has both `apply_style` and `render` + all panel builders).

**`__init__.py`** is intentionally minimal (`"""Visualization skills."""`) —
submodule imports work because Python resolves them via the package path.

### 2. Custom orchestrator

The default `AgentOrchestrator.execute_skill` returns echoes. Created
`FigureOrchestrator` in `run_figure_experiment.py` which dispatches
`skill_name` → the real Python function. 111 agents loaded successfully by
the default `_load_agents` scanner.

### 3. Synthetic multi-omics data

`generate_synthetic_data(seed=42)` produces:

- **`de_results`** (150 genes × {gene, baseMean, log2FoldChange, pvalue, padj}).
  25 genes forced DE, rest noise → 38 with `padj<0.05 & |LFC|>1` after BH FDR.
- **`expression`** (20 top DE genes × 60 samples; tumor vs normal shift matches
  the DE call).
- **`clinical`** (40 samples × age, stage, pERK, pAKT, MYC, Ki67).
- **`survival`** (40 × time, event, group) — group is MYC-high/low by median
  protein; time has a real MYC-driven shift baked in.
- **`correlation`** (numeric subset for the matrix).

### 4. Errors encountered and fixes

| # | Symptom | Cause | Fix |
| --- | --- | --- | --- |
| 1 | `ValueError: could not broadcast array (12,) → (13,)` | `n_de=25`, so `n_de//2=12` but `log2fc[12:25]` is length 13. | In `generate_synthetic_data`: use `size=n_de - n_de // 2` for the second half. |
| 2 | `ValueError: Unknown matplotlib operation: render` (raised at `matplotlib_skill.run`) | Concurrent-process overwrite had replaced my 200-line module with a 30-line stub that only handled `apply_style`. | Rewrote `matplotlib_skill.py` with both `render` and `apply_style` plus all panel builders. |
| 3 | execute_agent result was a coroutine | orchestrator `execute_agent` calls `agent.execute(task, ctx)` and only unwraps awaitables *if* isawaitable is true; sandbox wrapper used `asyncio.run` which cannot be called from a running loop (we weren't in one). | This was actually a side-effect of error #2 failing — the traceback through `_run_awaitable` confused the report. Once the skill call worked, `_run_awaitable` completed normally. |
| 4 | `seaborn_stylist_boxplot` reported `files=[]` | My condition `if out and ax is None: save_all(fig, out)` — `ax` was reassigned by `plt.subplots` so not None at save time. | Track `ax_was_provided` before the branch; save whenever `out` is truthy. |
| 5 | Volcano plot gene labels overlapped at peak | Straight `annotate(xytext=(offset))` pushed all labels into the same region. | Used `adjustText` library (`pip install adjustText`) — auto non-overlapping label placement with leader lines. |
| 6 | Volcano legend collided with gene labels | legend placed `loc="upper right"` in the data region. | Moved legend below the axes with `bbox_to_anchor=(0.0, -0.18), ncol=3`. |
| 7 | Correlation-panel `survival_months` x-tick label clipped | Tight-bbox save didn't account for the rotated label plus colorbar. | `fig.subplots_adjust(right=0.88)` in the correlation builder. |
| 8 | Seaborn boxplot came out with default seaborn rcParams (huge fonts, single colour) | `sns.set_style("ticks", …)` resets rcParams *after* I'd applied the Nature preset. | Re-apply `_apply_rc(style)` *after* `sns.set_style`. Also inject an Okabe-Ito default palette when caller doesn't pass one. |
| 9 | `pip install adjustText` went to Python 3.11 site-packages | `.venv`'s `pip` script is for 3.11 but `python` is 3.13. | Used `python -m pip install adjustText` so it lands in the 3.13 site-packages. |

### 5. produced artifacts

All written to `experiments/figure_generation/`:

| File | Size (KiB) | Description |
| --- | ---:| --- |
| `panel_a_volcano.{pdf,png,svg}` | 43 / 56 / 34 | Volcano plot: 150 genes, 18 up / 20 down (orange/blue Okabe-Ito, NS grey dashed thresholds, top 6 genes labelled with adjustText leader lines) |
| `panel_b_heatmap.{pdf,png,svg}` | 40 / 63 / 30 | Row z-scored RNA expression heatmap of top-20 DE genes × 60 samples, RdBu_r colormap, colorbar labelled "z-score" |
| `panel_c_kaplan_meier.{pdf,png,svg}` | 25 / 35 / 15 | KM survival MYC-high vs MYC-low with censoring ticks; log-rank χ² p = 0.028 displayed in-figure |
| `panel_d_correlation.{pdf,png,svg}` | 32 / 56 / 23 | Lower-triangle Pearson-r heatmap of age, pERK, pAKT, MYC, Ki67, survival_months with r values annotated |
| `panel_e_protein_boxplot.{pdf,png,svg}` | 18 / 22 / 14 | Boxplots of 4 protein markers across tumor stages, Okabe-Ito palette |
| `figure1_multipanel.{pdf,png,svg}` | 80 / 224 / 101 | Composed 2×2 multi-panel figure from panels a–d, mouth panel labels (bold, top-left), Nature double-column width (7.2 in) |
| `figure1_multipanel_nature_styled.{pdf,png,svg}` | 81 / 224 / 101 | Same figure after running `matplotlib_style.apply_style("nature")` — inlined into the layout_composer save path |
| `experiment.log` | 4 | Full step log |
| `experiment_summary.json` | 3.5 | Machine-readable step results + artifact list |

## Visual inspection results

### Final multi-panel figure (`figure1_multipanel.png`)

- **Panel a (volcano):** thresholds + labels legible without overlap; legend below x-axis with NS/Up/Down counts.
- **Panel b (heatmap):** clean column separation between tumor and normal clusters; y-ticks show italicised gene symbols (including TP53, KRAS, BRCA1, PTEN markers).
- **Panel c (KM):** textbook Kaplan-Meier. Censoring ticks visible, log-rank p-value inset, group colors distinct.
- **Panel d (correlation):** lower-triangle annotated heatmap; off-diagonal "survival_months" tick label is fully visible after the right-margin pad.

### Standalone protein boxplot (`panel_e_protein_boxplot.png`)
Four Okabe-Ito colors (blue/orange/green/pink), thin box lines (0.6 pt), outliers shown, Nature-style tick sizes.

## Verdict — can openScience make publication-ready figures?

**Yes — but only after writing real skills.** The agent layer (`agents/visualization/*.py`) is a working façade: it routes correct skill names + operations + payloads to the orchestrator, but the orchestrator's `execute_skill` is a stub that doesn't actually render anything. To get real PDFs out, you must:

1. Subclass `AgentOrchestrator` and override `execute_skill` to dispatch into real Python functions (or register them in a skill table — that's the pattern `FigureOrchestrator` uses).
2. Implement each skill module under `src/openscience/skills/visualization/`. The four skills needed here are only ~600 lines in total but they need to handle real-world plot concerns (label qui-repulsion, colorbar margin, Nature rcParams, multi-format save).

### What's missing for a true end-to-end "give me a figure" agent

The following gaps showed up:

1. **No skill registry / discovery.** Skills are referenced by string names
   (`"matplotlib"`, `"seaborn"`, …) from the agent classes, but there is no
   import machinery that maps a string to a callable. Every deployment has
   to subclass `AgentOrchestrator`.
2. **No parameter schema.** Agents pass arbitrary kwargs through. There's no
   validation that the data frame actually has the columns a panel builder
   needs (e.g. `time`, `event`, `group` for Kaplan-Meier). Bad input →
   `KeyError` from pandas instead of a friendly skill-level error.
3. **Four more panel types are referenced by name in the agent registry but
   unimplemented** — e.g. `blockVisualizer`, `graph_network_visualizer`,
   `plotly_specialist`, `interactive_dashboard`, `annotation_specialist`,
   `vector_graphics_editor`, `3d_visualizer`, `animation_generator`,
   `schematic_illustrator`. Only the four I needed are written.
4. **No persistent figure artifact model.** `Result.artifacts` is a `list[str]`
   of paths but the orchestrator never populates it from the skill results;
   I had to do it manually in the experiment runner.
5. **No raster-vs-vector heuristic.** A true publication formatter could
   detect heavy panels (scatter with 100k points, dense heatmaps) and
   rasterize them inside a vector PDF — right now PDF size grows linearly
   with point count.
6. **`matplotlib_stylist.apply_style` is one-way.** It sets rcParams
   globally but doesn't restore afterwards. Calling it once means every
   subsequent figure in the same process inherits those styles. That bit me
   between step 4 and step 5 (the seaborn boxplot briefly inherited the full
   Nature preset, which is actually what I wanted — happy accident — but a
   cleaner design would be `with plt.rc_context(…)`).
7. **Layout-composer sub-render calls duplicate rcParams application.** Each
   panel re-applies `_apply_rc(style)` (harmless but redundant).
8. **CVD accessibility is only reported, not enforced.** The
   `colorbrewer` skill returns a `cvd_safe` flag and a min-distance
   diagnostic, but nothing *refuses* an inaccessible palette.

## Recommendations

1. **Make `execute_skill` load skills via the existing
   `pkgutil.iter_modules(skills.__path__)`** the same way `_load_agents`
   works — then the user never needs to subclass.
2. Add `render(volcano | heatmap | kaplan_meier | correlation_matrix | box)`
   to `matplotlib_skill` (the version in this repo now has all of them) and
   register it as the default for `publication_formatter`.
3. Wire `Result.artifacts` from the skill's `saved_to` outputs so callers
   can enumerate produced files without globbing.
4. Add a tiny pytest that iterates every registered skill, calls `run` with
   a canonical minimal payload, and asserts it returns a figure or a dict —
   that would have caught the missing `render` branch immediately.

## Reproduce

```bash
cd /Users/srubaiat/openScience
source .venv/bin/activate
python -m pip install adjustText  # only extra dep not in requirements.txt
python experiments/figure_generation/run_figure_experiment.py
```

The script logs to both stdout and
`experiments/figure_generation/experiment.log`, and writes
`experiment_summary.json` listing every step's status, error (if any), and
the artifacts it produced.
